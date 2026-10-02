/* Linux native simulator of the SAME core used in the MCU firmware.
 * Binds loopback only. Local ARM and fault injection accepted only in this simulator.
 */
#include "ControlCore.hpp"
#include <sys/socket.h>
#include <netinet/in.h>
#include <unistd.h>
#include <fcntl.h>
#include <chrono>
#include <thread>
#include <iostream>
#include <string>
using namespace husky;
int main(int argc,char**argv){
 int port=argc>1?std::atoi(argv[1]):8765;int srv=socket(AF_INET,SOCK_STREAM,0),one=1;
 setsockopt(srv,SOL_SOCKET,SO_REUSEADDR,&one,sizeof one);sockaddr_in a{};a.sin_family=AF_INET;a.sin_port=htons(port);a.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
 if(bind(srv,(sockaddr*)&a,sizeof a)<0||listen(srv,1)<0){perror("listen");return 2;}
 std::cout<<"R01 native core simulator on 127.0.0.1:"<<port<<std::endl;
 while(true){
  int fd=accept(srv,nullptr,nullptr);if(fd<0)continue;fcntl(fd,F_SETFL,O_NONBLOCK);
  Controller c;Input in;bool sensorFault=false,wet=false,fold=false;std::string pending;
  auto begin=std::chrono::steady_clock::now();uint32_t last=0,report=0;
  for(;;){
   uint32_t now=uint32_t(std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now()-begin).count());
   char b[256];int n=recv(fd,b,sizeof b,0);if(n==0)break;
   if(n>0){pending.append(b,n);if(pending.size()>2048){c.trip("FRAME_TOO_LONG");pending.clear();}
    size_t pos;while((pos=pending.find('\n'))!=std::string::npos){std::string line=pending.substr(0,pos);pending.erase(0,pos+1);
     if(line=="SIM ARM")c.localArm(in,now);
     else if(line=="SIM SENSOR")sensorFault=true;
     else if(line=="SIM WET")wet=true;
     else if(line=="SIM FOLD")fold=true;
     else if(line=="SIM CLEAR"){sensorFault=wet=fold=false;in.c.fill(25);}
     else c.command(line.c_str(),in,now);
    }
   }
   if(uint32_t(now-last)>=100){float dt=(now-last)/1000.0f;last=now;
    for(int z=0;z<4;z++){float t=in.c[z*2];if(!std::isfinite(t))t=25;
     // Deliberately simple lumped plant, not validated heat transfer of a person.
     t+=dt*(0.09f*c.output().duty[z]-0.003f*(t-20));in.c[z*2]=in.c[z*2+1]=t;}
    if(sensorFault)in.c[0]=NAN;in.dry=!wet;in.deployed=!fold;in.sampledMs=now;c.step(in,now);
   }
   if(uint32_t(now-report)>=500){report=now;char s[192];c.status(s,sizeof s,in);if(send(fd,s,std::strlen(s),MSG_NOSIGNAL)<0)break;}
   std::this_thread::sleep_for(std::chrono::milliseconds(5));
  }
  close(fd);
 }
}
