#include "ControlCore.hpp"
#include <iostream>
#include <limits>
using namespace husky;
int n=0;
void check(bool b,const char* name){n++;std::cout<<(b?"PASS ":"FAIL ")<<name<<"\n";if(!b)std::exit(1);}
void active(Controller& c,Input& i){i.sampledMs=100;c.localArm(i,100);c.start(Mode::WORK,34,i,100);c.step(i,100);}
int main(){
 {Controller c;Input i;check(!c.output().relay,"boot-off");check(!c.start(Mode::WORK,34,i,0),"no-remote-arm");check(!c.command("H1 ARM",i,0),"arm-not-in-protocol");}
 {Controller c;Input i;active(c,i);check(c.output().relay&&c.output().duty[0]>0,"valid-start-heats");check(!c.start(Mode::WORK,34,i,101),"start-cannot-renew");c.stop();check(!c.output().relay,"stop-immediate");check(!c.armed(),"stop-disarms");}
 {Controller c;Input i;active(c,i);i.c[1]=40;i.sampledMs=200;c.step(i,200);check(c.mode()==Mode::FAULT&&!c.output().relay,"second-sensor-overheat");c.command("H1 STOP",i,200);check(c.mode()==Mode::FAULT,"stop-cannot-clear-fault");}
 for(int s=0;s<8;s++){Controller c;Input i;active(c,i);i.c[s]=NAN;i.sampledMs=200;c.step(i,200);check(c.mode()==Mode::FAULT,"each-sensor-disconnection");}
 for(int s=0;s<8;s++){Controller c;Input i;active(c,i);i.c[s]=50;i.sampledMs=200;c.step(i,200);check(c.mode()==Mode::FAULT,"each-sensor-hotspot");}
 {Controller c;Input i;active(c,i);i.c[0]=12;i.sampledMs=200;c.step(i,200);check(!std::strcmp(c.fault(),"SENSOR_MISMATCH"),"pair-mismatch");}
 for(int k=0;k<3;k++){Controller c;Input i;active(c,i);if(k==0)i.dry=false;if(k==1)i.deployed=false;if(k==2)i.safetyLoop=false;i.sampledMs=200;c.step(i,200);check(!c.output().relay,"physical-interlock");}
 {Controller c;Input i;active(c,i);for(uint32_t t=200;t<=5100;t+=100){i.sampledMs=t;c.step(i,t);}check(!std::strcmp(c.fault(),"LINK_TIMEOUT"),"lost-link-5s");}
 {Controller c;Input i;active(c,i);i.sampledMs=1000;c.step(i,1000);check(!std::strcmp(c.fault(),"LOOP_STALL"),"control-task-stall");}
 {Controller c;Input i;active(c,i);for(uint32_t t=200;t<=1300;t+=100)c.step(i,t);check(!std::strcmp(c.fault(),"STALE_SENSOR"),"stale-sample");}
 for(float v:{9.0f,14.0f,NAN}){Controller c;Input i;active(c,i);i.heaterV=v;i.sampledMs=200;c.step(i,200);check(!c.output().relay,"heater-voltage-range");}
 for(float v:{20.0f,30.0f,NAN}){Controller c;Input i;active(c,i);i.batteryV=v;i.sampledMs=200;c.step(i,200);check(!c.output().relay,"battery-voltage-range");}
 for(auto s:{"H1 START nan","H1 START inf","H1 START 99","H1 START 34x","H1 START ","H1 RESET","H1 START 27"}){Controller c;Input i;c.localArm(i,0);check(!c.command(s,i,0),"invalid-command-rejected");}
 {Controller c;Input i;active(c,i);c.command("H1 SLEEP",i,150);check(c.mode()==Mode::SLEEP&&!c.output().relay,"sleep-always-unheated");}
 {Controller c;Input i;active(c,i);for(uint32_t t=200;t<=1800200;t+=100){i.sampledMs=t;c.ping(t);c.step(i,t);}check(c.mode()==Mode::OFF&&!c.armed(),"30min-hard-deadline");}
 {Controller c;Input i;i.sampledMs=1;c.localArm(i,1);i.sampledMs=61002;c.step(i,61002);check(!c.start(Mode::WORK,34,i,61002),"arm-expires");}
 {Controller c;Input i;active(c,i);c.trip("TEST");check(c.localArm(i,100)&&c.mode()==Mode::OFF,"physical-reset-only");}
 {Controller c;Input i;i.sampledMs=0xffffff00u;c.localArm(i,0xffffff00u);c.start(Mode::WORK,34,i,0xffffff00u);c.step(i,0xffffff00u);i.sampledMs=44;c.ping(44);c.step(i,44);check(c.output().relay,"millis-rollover");}
 std::cout<<"TOTAL "<<n<<" PASS\n";
}
