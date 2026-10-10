cmake_minimum_required(VERSION 3.24)
project(foveabench_vulkan LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
find_package(Vulkan REQUIRED)
find_program(GLSLANG_EXECUTABLE glslangValidator REQUIRED)
set(SHADER_SOURCE ${CMAKE_CURRENT_SOURCE_DIR}/../../shaders/foveation.comp)
set(SPIRV_OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/foveation.comp.spv)
add_custom_command(OUTPUT ${SPIRV_OUTPUT}
    COMMAND ${GLSLANG_EXECUTABLE} -V -S comp -o ${SPIRV_OUTPUT} ${SHADER_SOURCE}
    DEPENDS ${SHADER_SOURCE}
    COMMENT "Compile SPIR-V: foveation.comp"
    VERBATIM)
add_custom_target(fb_shaders DEPENDS ${SPIRV_OUTPUT})
add_executable(fb_vk_compute main.cpp)
target_link_libraries(fb_vk_compute PRIVATE Vulkan::Vulkan)
add_dependencies(fb_vk_compute fb_shaders)
configure_file(${CMAKE_CURRENT_SOURCE_DIR}/../../shaders/foveation.comp
               ${CMAKE_CURRENT_BINARY_DIR}/foveation.comp COPYONLY)
