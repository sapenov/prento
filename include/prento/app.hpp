#pragma once
#include "core.hpp"
#include <atomic>
#include <chrono>
#include <csignal>
#include <map>
#include <string>

namespace prento {
using Clock=std::chrono::steady_clock;
inline std::uint64_t now_ns() {
    return std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now().time_since_epoch()).count();
}
extern std::atomic_bool stopping;
class Args {
    std::map<std::string,std::string> values_;
public:
    Args(int argc,char** argv);
    std::string str(const std::string& key,const std::string& fallback) const;
    std::uint64_t num(const std::string& key,std::uint64_t fallback) const;
    double real(const std::string& key,double fallback) const;
};
int collector(const Args&);
int producer(const Args&);
int sink(const Args&);
}
