#include "fanin/app.hpp"
#include <cmath>
#include <iostream>
#include <stdexcept>

namespace fanin {
std::atomic_bool stopping=false;
static_assert(std::atomic_bool::is_always_lock_free);
Args::Args(int argc,char** argv) {
    const std::map<std::string,std::vector<std::string>> allowed{
        {"collector",{"bind","port","metrics-port","sink","admission","policy","buffer-bytes","max-batch-bytes","timeout-ms","max-clients","priority-quota"}},
        {"producer",{"target","admission","duration-ms","rate","producers","critical-fraction","critical-bytes","bulk-bytes","queue-items","timeout-ms","seed","output","burst-factor","start-delay-ms"}},
        {"sink",{"bind","port","bytes-per-sec","max-batch-bytes","slow-factor","slow-start-ms","slow-ms","outage-start-ms","outage-ms"}}
    };
    auto command=allowed.find(argv[1]);
    if(command==allowed.end())throw std::invalid_argument("unknown command");
    if((argc-2)%2) throw std::invalid_argument("options need --name value pairs");
    for(int i=2;i<argc;i+=2) {
        std::string key=argv[i];
        if(!key.starts_with("--") || values_.contains(key.substr(2))) throw std::invalid_argument("invalid/duplicate option");
        bool recognized=false;
        for(const auto& name:command->second)if(name==key.substr(2))recognized=true;
        if(!recognized)throw std::invalid_argument("unknown option "+key);
        values_[key.substr(2)]=argv[i+1];
    }
}
std::string Args::str(const std::string& k,const std::string& fallback) const {
    auto it=values_.find(k);return it==values_.end()?fallback:it->second;
}
std::uint64_t Args::num(const std::string& k,std::uint64_t fallback) const {
    auto value=str(k,std::to_string(fallback));
    if(value.empty() || value[0]=='-') throw std::invalid_argument("invalid --"+k);
    std::size_t end=0; auto result=std::stoull(value,&end);
    if(end!=value.size()) throw std::invalid_argument("invalid --"+k);
    return result;
}
double Args::real(const std::string& k,double fallback) const {
    auto value=str(k,std::to_string(fallback)); std::size_t end=0;
    auto result=std::stod(value,&end);
    if(end!=value.size() || !std::isfinite(result)) throw std::invalid_argument("invalid --"+k);
    return result;
}
}
int main(int argc,char** argv) {
    try {
        std::signal(SIGINT,[](int){fanin::stopping=1;});
        std::signal(SIGTERM,[](int){fanin::stopping=1;});
        std::signal(SIGPIPE,SIG_IGN);
        if(argc<2 || std::string(argv[1])=="--help") {
            std::cout<<"fanin collector|producer|sink [--option value ...]\nSee README.md for documented options.\n";
            return argc<2?1:0;
        }
        fanin::Args args(argc,argv);
        std::string cmd=argv[1];
        if(cmd=="collector") return fanin::collector(args);
        if(cmd=="producer") return fanin::producer(args);
        if(cmd=="sink") return fanin::sink(args);
        throw std::invalid_argument("unknown command");
    } catch(const std::exception& e) { std::cerr<<"error: "<<e.what()<<'\n'; return 1; }
}
