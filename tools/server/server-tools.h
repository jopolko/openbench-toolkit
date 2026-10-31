#pragma once

#include "server-common.h"
#include "server-http.h"

#include <string>
#include <vector>

// Cross-platform run-and-capture helper (exec_shell_command's own backing
// implementation) - exposed here so other callers (the pentest-launch route
// in server.cpp) can reuse the same spawn/timeout/output-capture logic
// instead of a second copy of it.
struct run_proc_result {
    std::string output;
    int  exit_code = -1;
    bool timed_out = false;
};
run_proc_result run_process(
        const std::vector<std::string> & args,
        size_t max_output,
        int timeout_secs);

struct server_tool {
    std::string name;
    std::string display_name;
    bool permission_write = false;

    virtual ~server_tool() = default;
    virtual json get_definition() = 0;
    virtual json invoke(json params) = 0;

    json to_json();
};

struct server_tools {
    std::vector<std::unique_ptr<server_tool>> tools;

    void setup(const std::vector<std::string> & enabled_tools);
    json invoke(const std::string & name, const json & params);

    server_http_context::handler_t handle_get;
    server_http_context::handler_t handle_post;
};
