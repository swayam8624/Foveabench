// FoveaBench Phase 2: synchronous, headless Vulkan compute renderer.
// Output is an instrumented Vulkan *compute* workload, never hardware fragment VRS.
// Copyright (c) 2026 FoveaBench contributors. Apache-2.0 (repository license).
#include <vulkan/vulkan.h>

#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <numeric>
#include <sstream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>
namespace fs = std::filesystem;

// Vulkan structures are initialized explicitly and destroyed in reverse order.
#define VK_CHECK(call) do { VkResult r = (call); if (r != VK_SUCCESS) { \
    throw std::runtime_error(std::string(#call) + " failed with VkResult " + std::to_string(int(r))); } } while (0)

struct Settings {
    fs::path shader, trace, output;
    int width = 128, height = 72, max_frames = 16, device_index = -1;
    bool require_hardware = false;
};
struct Gaze { uint64_t t; float truth_x, truth_y, used_x, used_y; bool valid; };
struct Push { int width, height, mode, tile; float gaze_x, gaze_y, fovea, middle; };
static_assert(sizeof(Push) == 32, "Push constant packing must match shader");

std::string quote(const std::string& s) {
    std::string out = "\"";
    for (char c : s) {
        if (c == '\\' || c == '"') out += '\\';
        if (c == '\n' || c == '\r') out += ' ';
        else if (static_cast<unsigned char>(c) < 32) out += '?';
        else out += c;
    }
    return out + '"';
}
Settings parse(int argc, char** argv) {
    Settings s;
    for (int i=1;i<argc;i++) {
        std::string arg = argv[i];
        if (arg == "--require-hardware") { s.require_hardware = true; continue; }
        if (arg == "--help") {
            std::cout << "fb_vk_compute --shader <compiled.spv> --trace <trace.csv> --output <dir> "
                "[--width N --height N --frames N --device-index N --require-hardware]\n";
            std::exit(0);
        }
        if (i+1 >= argc) throw std::runtime_error("Missing value for " + arg);
        std::string v=argv[++i];
        if (arg == "--shader") s.shader=v;
        else if (arg == "--trace") s.trace=v;
        else if (arg == "--output") s.output=v;
        else if (arg == "--width") s.width=std::stoi(v);
        else if (arg == "--height") s.height=std::stoi(v);
        else if (arg == "--frames") s.max_frames=std::stoi(v);
        else if (arg == "--device-index") s.device_index=std::stoi(v);
        else throw std::runtime_error("Unknown option " + arg);
    }
    if (s.shader.empty()||s.trace.empty()||s.output.empty()) throw std::runtime_error("--shader --trace --output are required");
    if (s.width<32||s.height<32||s.width>4096||s.height>4096||s.max_frames<1||s.max_frames>100000)
        throw std::runtime_error("Invalid size or frames; allowed 32..4096 pixels and 1..100000 frames");
    if (fs::exists(s.output)) throw std::runtime_error("Refusing to overwrite existing results: " + s.output.string());
    return s;
}
std::vector<Gaze> read_trace(const fs::path& path, int max_frames) {
    std::ifstream in(path);
    if (!in) throw std::runtime_error("Cannot open trace " + path.string());
    std::string line; std::getline(in,line);
    if (!line.empty() && line.back() == '\r') line.pop_back(); // Python csv.writer uses CRLF by default.
    if (line != "timestamp_ns,truth_x,truth_y,used_x,used_y,valid")
        throw std::runtime_error("Trace header must be timestamp_ns,truth_x,truth_y,used_x,used_y,valid");
    std::vector<Gaze> out;
    while (std::getline(in,line) && (int)out.size()<max_frames) {
        if (line.empty()) continue;
        std::replace(line.begin(),line.end(),',',' ');
        std::istringstream ss(line);
        Gaze g{}; std::string valid;
        if (!(ss>>g.t>>g.truth_x>>g.truth_y>>g.used_x>>g.used_y>>valid))
            throw std::runtime_error("Malformed trace row");
        g.valid = valid=="1" || valid=="true" || valid=="True";
        if (!g.valid) throw std::runtime_error("Phase 2 requires valid predicted gaze or an explicit fallback trace");
        auto check_uv=[](float x){return std::isfinite(x)&&x>=0.f&&x<=1.f;};
        if (!check_uv(g.truth_x)||!check_uv(g.truth_y)||!check_uv(g.used_x)||!check_uv(g.used_y))
            throw std::runtime_error("Trace has invalid normalized gaze coordinates");
        if (!out.empty() && g.t<=out.back().t) throw std::runtime_error("Trace time must increase strictly");
        out.push_back(g);
    }
    if (out.empty()) throw std::runtime_error("Trace is empty");
    return out;
}
std::vector<char> read_bytes(const fs::path& path) {
    std::ifstream file(path, std::ios::binary|std::ios::ate);
    if (!file) throw std::runtime_error("Missing shader: " + path.string());
    std::streamoff len = file.tellg();
    if (len<4 || (len%4)!=0) throw std::runtime_error("Invalid SPIR-V byte count");
    std::vector<char> data(static_cast<size_t>(len));
    file.seekg(0); file.read(data.data(),len);
    if (!file) throw std::runtime_error("Failed to read shader");
    return data;
}
constexpr double PI=3.1415926535897932384626433832795;
std::array<double,3> ray(double u, double v) {
    double x=2*u-1, y=1-2*v, mag=std::sqrt(x*x+y*y+1);
    return {x/mag,y/mag,1/mag};
}
double separation(double u, double v, double gx, double gy) {
    auto a=ray(u,v), b=ray(gx,gy);
    return std::acos(std::clamp(a[0]*b[0]+a[1]*b[1]+a[2]*b[2], -1.0,1.0))*180.0/PI;
}
uint32_t pack(double r,double g,double b) {
    auto q=[](double x)->uint32_t {return static_cast<uint32_t>(std::round(std::clamp(x,0.0,1.0)*255.));};
    return q(r) | (q(g)<<8) | (q(b)<<16);
}
std::vector<uint32_t> scene(int w, int h, int frame, int kind) {
    std::vector<uint32_t> data(size_t(w)*h);
    for (int y=0;y<h;y++) for(int x=0;x<w;x++) {
        double u=double(x)/w, v=double(y)/h;
        if(kind==0) {
            double wave=std::sin(2*PI*(5*u+36*u*u+.07*frame));
            double stripe=std::cos(2*PI*(8*v+12*u*v));
            data[size_t(y)*w+x]=pack(.5+.45*wave,.5+.42*stripe,.5+.24*wave+.22*stripe);
        } else {
            double check=std::fmod(std::floor(u*42)+std::floor(v*25),2);
            double cx=.50+.10*std::sin(frame/8.0);
            double disk=(u-cx)*(u-cx)+(v-.48)*(v-.48)<.13*.13?1.:0.;
            double bar=std::abs(u-(.20+frame/(w*4.)))<.018?1.:0.;
            data[size_t(y)*w+x]=pack(.15+.7*check,.12+.75*disk,.15+.7*bar);
        }
    }
    return data;
}
struct Metric { double mse=0., weighted=0., foveal=0.; int mismatch=0, boundary_mismatch=0; uint64_t sample_count=0; };
Metric metrics(const std::vector<uint32_t>& src, const std::vector<uint32_t>& image, const Gaze& g,
               int w,int h,int mode,float gx,float gy) {
    Metric m; double wt=0, wmse=0, mse=0, fmse=0; int fn=0;
    for(int ty=0;ty<h;ty+=8) for(int tx=0;tx<w;tx+=8) {
        int x1=std::min(tx+8,w), y1=std::min(ty+8,h);
        double ux=(double((tx+x1-1)/2)+.5)/w, uv=(double((ty+y1-1)/2)+.5)/h;
        double a=separation(ux,uv, mode==1?.5:gx,mode==1?.5:gy);
        int r=mode==0?1:(a<=5.?1:(a<=15.?2:4));
        m.sample_count+=uint64_t((x1-tx+r-1)/r)*((y1-ty+r-1)/r);
    }
    for(int y=0;y<h;y++)for(int x=0;x<w;x++) {
        auto a=src[size_t(y)*w+x], b=image[size_t(y)*w+x];
        double se=0;
        for(int c=0;c<3;c++){
            double d=double((a>>(c*8))&255)-double((b>>(c*8))&255);
            se+=d*d/3;
        }
        if(a!=b) m.mismatch++;
        double theta=separation((x+.5)/w,(y+.5)/h,g.truth_x,g.truth_y);
        double weight=.01+std::exp(-.5*std::pow(theta/5.,2));
        mse+=se;wmse+=se*weight;wt+=weight;
        if(theta<=5) {fmse+=se;fn++;}
    }
    m.mse=mse/(w*h);m.weighted=wmse/wt;m.foveal=fn?fmse/fn:0;
    return m;
}
void write_ppm(const fs::path& p, const std::vector<uint32_t>& pix, int w,int h) {
    std::ofstream f(p,std::ios::binary);
    f<<"P6\n"<<w<<' '<<h<<"\n255\n";
    for (uint32_t x:pix){char c[3]={char(x&255),char((x>>8)&255),char((x>>16)&255)};f.write(c,3);}
    if(!f)throw std::runtime_error("Writing image failed");
}

// Owning context: command resources cleaned up after fence wait and GPU idle.
struct VulkanContext {
    VkInstance instance=VK_NULL_HANDLE; VkPhysicalDevice physical=VK_NULL_HANDLE;
    VkDevice device=VK_NULL_HANDLE; VkQueue queue=VK_NULL_HANDLE;
    uint32_t family=0, valid_bits=0; VkPhysicalDeviceProperties props{};
    VkCommandPool command_pool=VK_NULL_HANDLE; VkCommandBuffer cmd=VK_NULL_HANDLE;
    VkDescriptorSetLayout ds_layout=VK_NULL_HANDLE; VkDescriptorPool descriptor_pool=VK_NULL_HANDLE;
    VkDescriptorSet set=VK_NULL_HANDLE; VkPipelineLayout pipeline_layout=VK_NULL_HANDLE;
    VkPipeline pipeline=VK_NULL_HANDLE; VkShaderModule shader=VK_NULL_HANDLE;
    VkQueryPool query_pool=VK_NULL_HANDLE; VkFence fence=VK_NULL_HANDLE;
    VkBuffer source=VK_NULL_HANDLE, target=VK_NULL_HANDLE;
    VkDeviceMemory source_memory=VK_NULL_HANDLE,target_memory=VK_NULL_HANDLE;
    void* input_ptr=nullptr; void* output_ptr=nullptr;
    bool timestamp=false, has_vrs_extension=false;
    bool vrs_pipeline=false, vrs_attachment=false, vrs_primitive=false;
    ~VulkanContext() {
        if(device) vkDeviceWaitIdle(device);
        if(input_ptr)vkUnmapMemory(device,source_memory);
        if(output_ptr)vkUnmapMemory(device,target_memory);
        if(fence)vkDestroyFence(device,fence,nullptr);
        if(query_pool)vkDestroyQueryPool(device,query_pool,nullptr);
        if(pipeline)vkDestroyPipeline(device,pipeline,nullptr);
        if(shader)vkDestroyShaderModule(device,shader,nullptr);
        if(pipeline_layout)vkDestroyPipelineLayout(device,pipeline_layout,nullptr);
        if(descriptor_pool)vkDestroyDescriptorPool(device,descriptor_pool,nullptr);
        if(ds_layout)vkDestroyDescriptorSetLayout(device,ds_layout,nullptr);
        if(source)vkDestroyBuffer(device,source,nullptr);
        if(target)vkDestroyBuffer(device,target,nullptr);
        if(source_memory)vkFreeMemory(device,source_memory,nullptr);
        if(target_memory)vkFreeMemory(device,target_memory,nullptr);
        if(command_pool)vkDestroyCommandPool(device,command_pool,nullptr);
        if(device)vkDestroyDevice(device,nullptr);
        if(instance)vkDestroyInstance(instance,nullptr);
    }
    uint32_t memory_type(uint32_t allowed) {
        VkPhysicalDeviceMemoryProperties m{};vkGetPhysicalDeviceMemoryProperties(physical,&m);
        for(uint32_t i=0;i<m.memoryTypeCount;i++)
            if ((allowed&(1u<<i)) && (m.memoryTypes[i].propertyFlags &
                (VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|VK_MEMORY_PROPERTY_HOST_COHERENT_BIT)) ==
                (VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|VK_MEMORY_PROPERTY_HOST_COHERENT_BIT))return i;
        throw std::runtime_error("No HOST_VISIBLE|HOST_COHERENT Vulkan memory. Device unsupported in this backend.");
    }
    void make_buffer(VkDeviceSize bytes,VkBuffer& buffer,VkDeviceMemory& memory,void*& mapped) {
        VkBufferCreateInfo info{VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO};
        info.size=bytes; info.usage=VK_BUFFER_USAGE_STORAGE_BUFFER_BIT; info.sharingMode=VK_SHARING_MODE_EXCLUSIVE;
        VK_CHECK(vkCreateBuffer(device,&info,nullptr,&buffer));
        VkMemoryRequirements req{};vkGetBufferMemoryRequirements(device,buffer,&req);
        VkMemoryAllocateInfo alloc{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};
        alloc.allocationSize=req.size; alloc.memoryTypeIndex=memory_type(req.memoryTypeBits);
        VK_CHECK(vkAllocateMemory(device,&alloc,nullptr,&memory));
        VK_CHECK(vkBindBufferMemory(device,buffer,memory,0));
        VK_CHECK(vkMapMemory(device,memory,0,req.size,0,&mapped));
    }
    void initialize(const Settings& s) {
        VkApplicationInfo app{VK_STRUCTURE_TYPE_APPLICATION_INFO};app.pApplicationName="FoveaBench";
        app.applicationVersion=VK_MAKE_VERSION(0,2,0);app.apiVersion=VK_API_VERSION_1_1;
        VkInstanceCreateInfo ci{VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO};ci.pApplicationInfo=&app;
        VK_CHECK(vkCreateInstance(&ci,nullptr,&instance));
        uint32_t count=0;VK_CHECK(vkEnumeratePhysicalDevices(instance,&count,nullptr));
        if(!count)throw std::runtime_error("No Vulkan devices; install Mesa lavapipe or a hardware Vulkan driver");
        std::vector<VkPhysicalDevice> devices(count);
        VK_CHECK(vkEnumeratePhysicalDevices(instance,&count,devices.data()));
        // Automatically prefer a real GPU with compute; CPU device is valid for compatibility ONLY.
        int best=-1;bool hardware=false;
        for(uint32_t i=0;i<count;i++){
            VkPhysicalDeviceProperties pr{};vkGetPhysicalDeviceProperties(devices[i],&pr);
            uint32_t qcount=0;vkGetPhysicalDeviceQueueFamilyProperties(devices[i],&qcount,nullptr);
            std::vector<VkQueueFamilyProperties> qs(qcount);
            vkGetPhysicalDeviceQueueFamilyProperties(devices[i],&qcount,qs.data());
            bool compute=false;for(auto q:qs)if(q.queueFlags&VK_QUEUE_COMPUTE_BIT)compute=true;
            if(!compute)continue;
            bool hw=pr.deviceType!=VK_PHYSICAL_DEVICE_TYPE_CPU;
            if((s.device_index<0 && (best<0 || (hw&&!hardware))) || (s.device_index==int(i))) {
                best=int(i);hardware=hw;
            }
        }
        if(best<0)throw std::runtime_error("No selected Vulkan compute-capable device");
        if(s.device_index>=0 && best!=s.device_index)throw std::runtime_error("Selected device unavailable or lacks compute support");
        physical=devices[best];vkGetPhysicalDeviceProperties(physical,&props);
        if(s.require_hardware && props.deviceType==VK_PHYSICAL_DEVICE_TYPE_CPU)
            throw std::runtime_error("--require-hardware set, but selected Vulkan device is CPU/software");
        uint32_t qcount=0;vkGetPhysicalDeviceQueueFamilyProperties(physical,&qcount,nullptr);
        std::vector<VkQueueFamilyProperties> qs(qcount);vkGetPhysicalDeviceQueueFamilyProperties(physical,&qcount,qs.data());
        bool found=false;for(uint32_t i=0;i<qcount;i++)if(qs[i].queueFlags&VK_QUEUE_COMPUTE_BIT){
            if(!found || (qs[i].timestampValidBits>0 && !valid_bits)) {family=i;valid_bits=qs[i].timestampValidBits;found=true;}
        }
        timestamp=valid_bits>0 && props.limits.timestampComputeAndGraphics;
        uint32_t ec=0;VK_CHECK(vkEnumerateDeviceExtensionProperties(physical,nullptr,&ec,nullptr));
        std::vector<VkExtensionProperties> ext(ec);
        VK_CHECK(vkEnumerateDeviceExtensionProperties(physical,nullptr,&ec,ext.data()));
        for(const auto& e:ext)if(std::strcmp(e.extensionName,"VK_KHR_fragment_shading_rate")==0)has_vrs_extension=true;
        if(has_vrs_extension){
            VkPhysicalDeviceFragmentShadingRateFeaturesKHR f{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_FRAGMENT_SHADING_RATE_FEATURES_KHR};
            VkPhysicalDeviceFeatures2 f2{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_FEATURES_2}; f2.pNext=&f;
            vkGetPhysicalDeviceFeatures2(physical,&f2);
            vrs_pipeline=f.pipelineFragmentShadingRate;
            vrs_attachment=f.attachmentFragmentShadingRate;
            vrs_primitive=f.primitiveFragmentShadingRate;
        }
        float priority=1.;VkDeviceQueueCreateInfo qi{VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO};
        qi.queueFamilyIndex=family;qi.queueCount=1;qi.pQueuePriorities=&priority;
        VkDeviceCreateInfo di{VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO};di.queueCreateInfoCount=1;di.pQueueCreateInfos=&qi;
        VK_CHECK(vkCreateDevice(physical,&di,nullptr,&device));
        vkGetDeviceQueue(device,family,0,&queue);
        VkDeviceSize sz=VkDeviceSize(s.width)*s.height*sizeof(uint32_t);
        make_buffer(sz,source,source_memory,input_ptr);
        make_buffer(sz,target,target_memory,output_ptr);
        std::array<VkDescriptorSetLayoutBinding,2> binds{};
        for(int i=0;i<2;i++){binds[i].binding=i;binds[i].descriptorType=VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
            binds[i].descriptorCount=1;binds[i].stageFlags=VK_SHADER_STAGE_COMPUTE_BIT;}
        VkDescriptorSetLayoutCreateInfo dli{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO};
        dli.bindingCount=2;dli.pBindings=binds.data();
        VK_CHECK(vkCreateDescriptorSetLayout(device,&dli,nullptr,&ds_layout));
        VkDescriptorPoolSize poolsize{VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,2};
        VkDescriptorPoolCreateInfo dpi{VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO};
        dpi.poolSizeCount=1;dpi.pPoolSizes=&poolsize;dpi.maxSets=1;
        VK_CHECK(vkCreateDescriptorPool(device,&dpi,nullptr,&descriptor_pool));
        VkDescriptorSetAllocateInfo sai{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO};
        sai.descriptorPool=descriptor_pool;sai.descriptorSetCount=1;sai.pSetLayouts=&ds_layout;
        VK_CHECK(vkAllocateDescriptorSets(device,&sai,&set));
        VkDescriptorBufferInfo ib{source,0,sz},ob{target,0,sz};
        std::array<VkWriteDescriptorSet,2> writes{};
        for(int i=0;i<2;i++){writes[i].sType=VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;writes[i].dstSet=set;
            writes[i].dstBinding=i;writes[i].descriptorCount=1;writes[i].descriptorType=VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
            writes[i].pBufferInfo=i==0?&ib:&ob;}
        vkUpdateDescriptorSets(device,2,writes.data(),0,nullptr);
        VkPushConstantRange push{VK_SHADER_STAGE_COMPUTE_BIT,0,sizeof(Push)};
        VkPipelineLayoutCreateInfo pli{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};
        pli.setLayoutCount=1;pli.pSetLayouts=&ds_layout;pli.pushConstantRangeCount=1;pli.pPushConstantRanges=&push;
        VK_CHECK(vkCreatePipelineLayout(device,&pli,nullptr,&pipeline_layout));
        auto spirv=read_bytes(s.shader);
        VkShaderModuleCreateInfo sm{VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO};
        sm.codeSize=spirv.size();sm.pCode=reinterpret_cast<const uint32_t*>(spirv.data());
        VK_CHECK(vkCreateShaderModule(device,&sm,nullptr,&shader));
        VkPipelineShaderStageCreateInfo st{VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO};
        st.stage=VK_SHADER_STAGE_COMPUTE_BIT;st.module=shader;st.pName="main";
        VkComputePipelineCreateInfo pi{VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO};
        pi.stage=st;pi.layout=pipeline_layout;
        VK_CHECK(vkCreateComputePipelines(device,VK_NULL_HANDLE,1,&pi,nullptr,&pipeline));
        VkCommandPoolCreateInfo cp{VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO};
        cp.flags=VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;cp.queueFamilyIndex=family;
        VK_CHECK(vkCreateCommandPool(device,&cp,nullptr,&command_pool));
        VkCommandBufferAllocateInfo ai{VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO};
        ai.commandPool=command_pool;ai.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY;ai.commandBufferCount=1;
        VK_CHECK(vkAllocateCommandBuffers(device,&ai,&cmd));
        if(timestamp){VkQueryPoolCreateInfo qp{VK_STRUCTURE_TYPE_QUERY_POOL_CREATE_INFO};
            qp.queryType=VK_QUERY_TYPE_TIMESTAMP;qp.queryCount=2;
            VK_CHECK(vkCreateQueryPool(device,&qp,nullptr,&query_pool));}
        VkFenceCreateInfo fi{VK_STRUCTURE_TYPE_FENCE_CREATE_INFO};
        VK_CHECK(vkCreateFence(device,&fi,nullptr,&fence));
    }
    // The GPU timing bracket is deliberately restricted to one compute dispatch.
    double dispatch(const std::vector<uint32_t>& input,std::vector<uint32_t>& output,const Push& push) {
        VkDeviceSize bytes=VkDeviceSize(input.size())*sizeof(uint32_t);
        std::memcpy(input_ptr,input.data(),size_t(bytes));
        VK_CHECK(vkResetFences(device,1,&fence));
        VK_CHECK(vkResetCommandBuffer(cmd,0));
        VkCommandBufferBeginInfo bi{VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};
        bi.flags=VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
        VK_CHECK(vkBeginCommandBuffer(cmd,&bi));
        VkMemoryBarrier host{VK_STRUCTURE_TYPE_MEMORY_BARRIER};
        host.srcAccessMask=VK_ACCESS_HOST_WRITE_BIT;host.dstAccessMask=VK_ACCESS_SHADER_READ_BIT;
        vkCmdPipelineBarrier(cmd,VK_PIPELINE_STAGE_HOST_BIT,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,0,
                             1,&host,0,nullptr,0,nullptr);
        vkCmdBindPipeline(cmd,VK_PIPELINE_BIND_POINT_COMPUTE,pipeline);
        vkCmdBindDescriptorSets(cmd,VK_PIPELINE_BIND_POINT_COMPUTE,pipeline_layout,0,1,&set,0,nullptr);
        vkCmdPushConstants(cmd,pipeline_layout,VK_SHADER_STAGE_COMPUTE_BIT,0,sizeof(Push),&push);
        if(timestamp){vkCmdResetQueryPool(cmd,query_pool,0,2);
            vkCmdWriteTimestamp(cmd,VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,query_pool,0);}
        vkCmdDispatch(cmd,(push.width+7)/8,(push.height+7)/8,1);
        if(timestamp)vkCmdWriteTimestamp(cmd,VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT,query_pool,1);
        VkMemoryBarrier gpu{VK_STRUCTURE_TYPE_MEMORY_BARRIER};
        gpu.srcAccessMask=VK_ACCESS_SHADER_WRITE_BIT;gpu.dstAccessMask=VK_ACCESS_HOST_READ_BIT;
        vkCmdPipelineBarrier(cmd,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,VK_PIPELINE_STAGE_HOST_BIT,0,
                             1,&gpu,0,nullptr,0,nullptr);
        VK_CHECK(vkEndCommandBuffer(cmd));
        VkSubmitInfo si{VK_STRUCTURE_TYPE_SUBMIT_INFO};si.commandBufferCount=1;si.pCommandBuffers=&cmd;
        VK_CHECK(vkQueueSubmit(queue,1,&si,fence));
        VK_CHECK(vkWaitForFences(device,1,&fence,VK_TRUE,UINT64_MAX));
        std::memcpy(output.data(),output_ptr,size_t(bytes));
        if(!timestamp)return std::numeric_limits<double>::quiet_NaN();
        uint64_t tick[2]={};
        VK_CHECK(vkGetQueryPoolResults(device,query_pool,0,2,sizeof(tick),tick,sizeof(uint64_t),
                                      VK_QUERY_RESULT_64_BIT|VK_QUERY_RESULT_WAIT_BIT));
        uint64_t mask=valid_bits>=64?~uint64_t(0):((uint64_t(1)<<valid_bits)-1);
        uint64_t dt=(tick[1]-tick[0]) & mask;
        return dt*double(props.limits.timestampPeriod)/1e6;
    }
};

int main(int argc,char** argv) {
    try {
        Settings s=parse(argc,argv);
        auto gaze=read_trace(s.trace,s.max_frames);
        auto spirv=read_bytes(s.shader);
        VulkanContext vk; vk.initialize(s);
        fs::create_directories(s.output/"frames");
        std::ofstream csv(s.output/"frames.csv");
        csv<<"scene,policy,frame_index,timestamp_ns,truth_x,truth_y,used_x,used_y,device_dispatch_ms,"
               "image_mse,weighted_mse,foveal_mse,sample_fraction_proxy,pixel_mismatch\n";
        csv<<std::setprecision(12);
        int rows=0,max_full_mismatch=0; double aggregate_weighted=0;
        constexpr std::array<const char*,4> modes={"full","fixed","tracked","tracked_lag40"};
        for(int scene_index=0;scene_index<2;scene_index++){
            for(int i=0;i<int(gaze.size());i++){
                const auto& g=gaze[i]; auto input=scene(s.width,s.height,i,scene_index);
                for(int mode=0;mode<4;mode++){
                    Gaze sample=g;
                    if(mode==3){
                        uint64_t t=g.t>=40000000?g.t-40000000:0;
                        for(int j=i;j>=0;j--)if(gaze[j].t<=t){sample=gaze[j];break;}
                    }
                    Push push{s.width,s.height,mode,8,sample.used_x,sample.used_y,5.f,15.f};
                    std::vector<uint32_t> output(input.size());
                    double gpu=vk.dispatch(input,output,push);
                    auto m=metrics(input,output,g,s.width,s.height,mode,push.gaze_x,push.gaze_y);
                    if(mode==0)max_full_mismatch=std::max(max_full_mismatch,m.mismatch);
                    csv<<(scene_index==0?"chirp":"edges")<<','<<modes[size_t(mode)]<<','<<i<<','<<g.t<<','
                       <<g.truth_x<<','<<g.truth_y<<','<<push.gaze_x<<','<<push.gaze_y<<',';
                    if(std::isfinite(gpu))csv<<gpu;
                    csv<<','<<m.mse<<','<<m.weighted<<','<<m.foveal<<','
                       <<double(m.sample_count)/input.size()<<','<<m.mismatch<<'\n';
                    if(i==0 || i==int(gaze.size())/2)
                        write_ppm(s.output/"frames"/(std::string(scene_index==0?"chirp_":"edges_")+
                              modes[size_t(mode)]+"_"+std::to_string(i)+".ppm"),output,s.width,s.height);
                    rows++;aggregate_weighted+=m.weighted;
                }
            }
        }
        csv.close();
        if(max_full_mismatch!=0)throw std::runtime_error("GPU full-resolution output differs from reference input!");
        bool software=vk.props.deviceType==VK_PHYSICAL_DEVICE_TYPE_CPU;
        std::ofstream man(s.output/"manifest.json");
        man<<"{\n  \"suite\": \"FB-RENDER-01/2.0\",\n  \"workload\": \"headless-vulkan-compute-image-space\",\n"
              "  \"actual_hardware_vrs\": false,\n  \"actual_fragment_shader_invocations_measured\": false,\n"
              "  \"device_name\": "<<quote(vk.props.deviceName)<<",\n"
              "  \"vendor_id\": "<<vk.props.vendorID<<", \"device_id\": "<<vk.props.deviceID<<",\n"
              "  \"driver_version\": "<<vk.props.driverVersion<<",\n"
              "  \"api_version\": "<<quote(std::to_string(VK_API_VERSION_MAJOR(vk.props.apiVersion))+"."+
              std::to_string(VK_API_VERSION_MINOR(vk.props.apiVersion))+"."+
              std::to_string(VK_API_VERSION_PATCH(vk.props.apiVersion)))<<",\n"
              "  \"device_type\": "<<quote(software?"software_cpu":
                    vk.props.deviceType==VK_PHYSICAL_DEVICE_TYPE_DISCRETE_GPU?"discrete_gpu":
                    vk.props.deviceType==VK_PHYSICAL_DEVICE_TYPE_INTEGRATED_GPU?"integrated_gpu":"other")<<",\n"
              "  \"hardware_score_eligible\": "<<(software?"false":"true")<<",\n"
              "  \"vrs_extension_advertised\": "<<(vk.has_vrs_extension?"true":"false")<<",\n"
              "  \"vrs_pipeline_feature\": "<<(vk.vrs_pipeline?"true":"false")<<",\n"
              "  \"vrs_attachment_feature\": "<<(vk.vrs_attachment?"true":"false")<<",\n"
              "  \"vrs_primitive_feature\": "<<(vk.vrs_primitive?"true":"false")<<",\n"
              "  \"timestamp_query_available\": "<<(vk.timestamp?"true":"false")<<",\n"
              "  \"timestamp_valid_bits\": "<<vk.valid_bits<<",\n"
              "  \"timestamp_period_ns\": "<<vk.props.limits.timestampPeriod<<",\n"
              "  \"gpu_timestamp_label\": "<<quote(vk.timestamp?"Vulkan-reported device dispatch time (may be CPU software driver)":"unsupported")<<",\n"
              "  \"gpu_time_is_full_frame_latency\": false,\n"
              "  \"scene_origin\": \"deterministic procedural diagnostic\",\n"
              "  \"resolution\": ["<<s.width<<","<<s.height<<"],\n"
              "  \"trace_frames\": "<<gaze.size()<<", \"frame_policy_evaluations\": "<<rows<<",\n"
              "  \"full_reference_pixel_mismatch_max\": "<<max_full_mismatch<<",\n"
              "  \"results_class\": "<<quote(software?"software-vulkan-functional":"native-vulkan-compute-technical")<<",\n"
              "  \"limitations\": [\"Not a graphics rasterization pipeline or VRS\","
              "\"All pixels execute compute invocations\",\"Not calibrated eye tracking\","
              "\"Not a representative XR scene or VR headset\",\"No motion-to-photon measurement\"]\n} \n";
        man.close();
        std::ofstream status(s.output/"STATUS.md");
        status<<"# Phase 2 execution ledger\n\n- Shader compilation: PASSED (SPIR-V loaded)\n"
              "- Vulkan queue, dispatch, readback: PASSED\n"
              "- Full-resolution bytewise invariant: "<<(max_full_mismatch?"FAIL":"PASS")<<"\n"
              "- Vulkan GPU timestamps: "<<(vk.timestamp?"AVAILABLE":"UNAVAILABLE")<<"\n"
              "- Device: "<<vk.props.deviceName<<"\n"
              "- Hardware VRS: NOT IMPLEMENTED (feature probed only)\n"
              "- ILLIXR integration: EXTERNAL INTERCHANGE ONLY (no source modifications)\n"
              "- Live eye tracking / headset latency: NOT MEASURED\n";
        std::cout<<"FB-RENDER-01 PASS: "<<rows<<" Vulkan dispatches on "<<vk.props.deviceName
                 <<"; device="<<(software?"SOFTWARE":"HARDWARE")
                 <<"; timestamp="<<(vk.timestamp?"available":"unavailable")<<"\n";
        return 0;
    } catch(const std::exception& e) {std::cerr<<"FB-RENDER-01 FAIL: "<<e.what()<<"\n";return 1;}
}
