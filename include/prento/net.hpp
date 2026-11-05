#pragma once
#include "app.hpp"
#include <arpa/inet.h>
#include <netdb.h>
#include <netinet/tcp.h>
#include <poll.h>
#include <sys/socket.h>
#include <unistd.h>
#include <array>
#include <cerrno>
#include <cstring>
#include <limits>
#include <stdexcept>

namespace prento {
class Socket {
    int fd_=-1;
public:
    explicit Socket(int fd=-1):fd_(fd) {}
    ~Socket() { if(fd_>=0) ::close(fd_); }
    Socket(const Socket&)=delete;
    Socket& operator=(const Socket&)=delete;
    Socket(Socket&& s) noexcept:fd_(s.fd_) { s.fd_=-1; }
    Socket& operator=(Socket&& s) noexcept {
        if(this!=&s) { if(fd_>=0) ::close(fd_); fd_=s.fd_; s.fd_=-1; } return *this;
    }
    int get() const { return fd_; }
    explicit operator bool() const { return fd_>=0; }
};
inline void io(int fd,void* data,std::size_t bytes,bool writing,int timeout=10000) {
    auto end=Clock::now()+std::chrono::milliseconds(timeout);
    auto* p=static_cast<char*>(data);
    while(bytes) {
        auto left=std::chrono::duration_cast<std::chrono::milliseconds>(end-Clock::now()).count();
        if(left<=0) throw std::runtime_error("socket deadline exceeded");
        pollfd f{fd,static_cast<short>(writing?POLLOUT:POLLIN),0};
        int r=::poll(&f,1,static_cast<int>(left));
        if(r<0 && errno==EINTR) continue;
        if(r<=0) throw std::runtime_error("socket timeout/poll failure");
        auto n=writing? ::send(fd,p,bytes,MSG_NOSIGNAL|MSG_DONTWAIT)
                      : ::recv(fd,p,bytes,MSG_DONTWAIT);
        if(n<0 && (errno==EINTR || errno==EAGAIN || errno==EWOULDBLOCK)) continue;
        if(n<=0) throw std::runtime_error("peer closed or socket failed");
        p+=n; bytes-=static_cast<std::size_t>(n);
    }
}
inline void send_bytes(int fd,std::string_view s,int timeout=10000) {
    io(fd,const_cast<char*>(s.data()),s.size(),true,timeout);
}
inline Socket listen_on(unsigned port,const std::string& bind="127.0.0.1") {
    Socket s(::socket(AF_INET,SOCK_STREAM,0));
    if(!s) throw std::runtime_error("socket: "+std::string(std::strerror(errno)));
    int yes=1;
    ::setsockopt(s.get(),SOL_SOCKET,SO_REUSEADDR,&yes,sizeof(yes));
    sockaddr_in a{}; a.sin_family=AF_INET; a.sin_port=htons(static_cast<uint16_t>(port));
    if(::inet_pton(AF_INET,bind.c_str(),&a.sin_addr)!=1) throw std::invalid_argument("invalid IPv4 bind address");
    if(::bind(s.get(),reinterpret_cast<sockaddr*>(&a),sizeof(a)) || ::listen(s.get(),256))
        throw std::runtime_error("bind/listen: "+std::string(std::strerror(errno)));
    return s;
}
inline int accept_ready(int fd,int timeout=100) {
    pollfd p{fd,POLLIN,0};
    if(::poll(&p,1,timeout)<=0) return -1;
    int result=::accept(fd,nullptr,nullptr);
    if(result>=0) { int yes=1; ::setsockopt(result,IPPROTO_TCP,TCP_NODELAY,&yes,sizeof(yes)); }
    return result;
}
inline Socket connect_to(const std::string& target,int timeout=10000) {
    auto pos=target.rfind(':');
    if(pos==std::string::npos) throw std::invalid_argument("endpoint must be host:port");
    auto host=target.substr(0,pos), port=target.substr(pos+1);
    addrinfo hints{},*raw=nullptr; hints.ai_family=AF_INET; hints.ai_socktype=SOCK_STREAM;
    if(::getaddrinfo(host.c_str(),port.c_str(),&hints,&raw)) throw std::runtime_error("cannot resolve endpoint");
    struct Guard { addrinfo* p; ~Guard(){ ::freeaddrinfo(p); } } guard{raw};
    for(auto* a=raw;a;a=a->ai_next) {
        Socket s(::socket(a->ai_family,SOCK_STREAM|SOCK_NONBLOCK,0));
        if(!s) continue;
        int r=::connect(s.get(),a->ai_addr,a->ai_addrlen);
        if(r && errno!=EINPROGRESS) continue;
        pollfd p{s.get(),POLLOUT,0};
        if(::poll(&p,1,timeout)<=0) continue;
        int err=0; socklen_t len=sizeof(err);
        if(::getsockopt(s.get(),SOL_SOCKET,SO_ERROR,&err,&len) || err) continue;
        int yes=1; ::setsockopt(s.get(),IPPROTO_TCP,TCP_NODELAY,&yes,sizeof(yes));
        return s;
    }
    throw std::runtime_error("cannot connect to "+target);
}
enum Type:std::uint8_t { Announce=1,Grant=2,Ack=3,Reject=4 };
struct Header {
    std::uint8_t type=Announce;
    bool critical=false,credit=false;
    std::uint64_t id=0;
    std::uint32_t bytes=0,hash=0;
    std::uint64_t intended_ns=0;
};
inline std::array<unsigned char,32> encode(const Header& h) {
    std::array<unsigned char,32> a{};
    auto put=[&](int off,std::uint64_t v,int count){ for(int i=count-1;i>=0;--i){a[off+i]=v&255;v>>=8;} };
    put(0,0x46414e31,4); a[4]=1; a[5]=h.type; a[6]=h.critical; a[7]=h.credit;
    put(8,h.id,8);put(16,h.bytes,4);put(20,h.hash,4);put(24,h.intended_ns,8); return a;
}
inline void send_header(int fd,const Header& h,int timeout=10000) {
    auto bytes=encode(h); io(fd,bytes.data(),bytes.size(),true,timeout);
}
inline Header read_header(int fd,int timeout=10000) {
    std::array<unsigned char,32> a{};io(fd,a.data(),a.size(),false,timeout);
    auto get=[&](int off,int count){std::uint64_t v=0;for(int i=0;i<count;++i)v=(v<<8)|a[off+i];return v;};
    if(get(0,4)!=0x46414e31 || a[4]!=1 || a[6]>1 || a[7]>1 || a[5]<1 || a[5]>4)
        throw std::runtime_error("invalid frame header");
    return Header{a[5],bool(a[6]),bool(a[7]),get(8,8),static_cast<std::uint32_t>(get(16,4)),
                  static_cast<std::uint32_t>(get(20,4)),get(24,8)};
}
// Idle persistent sessions are not failed by a frame deadline. Once any byte
// arrives, the whole frame must arrive within timeout (bounds partial senders).
inline Header next_header(int fd,int timeout=10000) {
    while(!stopping) {
        pollfd p{fd,POLLIN,0};
        auto result=::poll(&p,1,100);
        if(result<0 && errno==EINTR)continue;
        if(result<0)throw std::runtime_error("idle-session poll failed");
        if(result>0)return read_header(fd,timeout);
    }
    throw std::runtime_error("server stopping");
}
inline int bounded_int(std::uint64_t value,const char* name,int low,int high) {
    if(value<static_cast<std::uint64_t>(low) || value>static_cast<std::uint64_t>(high))
        throw std::invalid_argument(std::string(name)+" out of range");
    return static_cast<int>(value);
}
}
