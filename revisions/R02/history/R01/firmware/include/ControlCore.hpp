#pragma once
#include <array>
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <cstdlib>
namespace husky {
enum class Mode { OFF, WORK, PREHEAT, SLEEP, FAULT };
struct Input {
  std::array<float,8> c{25,25,25,25,25,25,25,25};
  float batteryV=25.6f, heaterV=12;
  bool deployed=true, dry=true, safetyLoop=true;
  uint32_t sampledMs=0;
};
struct Output { std::array<float,4> duty{}; bool relay=false; };
class Controller {
  Mode m_=Mode::OFF; const char* fault_="NONE";
  Output out_; bool armed_=false, ticked_=false;
  uint32_t armedMs_=0,startMs_=0,pingMs_=0,lastMs_=0;
  float target_=34; std::array<float,4> integ_{};
  void zero(){out_={};integ_.fill(0);}
public:
  static constexpr uint32_t LEASE=5000,SESSION=1800000,PREHEAT=600000;
  Mode mode()const{return m_;} const Output& output()const{return out_;}
  const char* fault()const{return fault_;} bool armed()const{return armed_;}
  float target()const{return target_;}
  const char* modeName()const {
    switch(m_){case Mode::WORK:return "WORK";case Mode::PREHEAT:return "PREHEAT";
      case Mode::SLEEP:return "SLEEP";case Mode::FAULT:return "FAULT";default:return "OFF";}
  }
  const char* unsafe(const Input& i,uint32_t now)const {
    if(!i.safetyLoop)return "SAFETY_LOOP";
    if(!i.dry)return "WET";
    if(!i.deployed)return "FOLD";
    if(uint32_t(now-i.sampledMs)>1000)return "STALE_SENSOR";
    if(!std::isfinite(i.batteryV)||i.batteryV<21.0f||i.batteryV>29.5f)return "BATTERY";
    if(!std::isfinite(i.heaterV)||i.heaterV<10.8f||i.heaterV>13.2f)return "HEATER_SUPPLY";
    for(int z=0;z<4;z++){
      float a=i.c[2*z],b=i.c[2*z+1];
      if(!std::isfinite(a)||!std::isfinite(b)||a< -15||b< -15||a>80||b>80)return "SENSOR";
      if(a>=40||b>=40)return "OVERTEMP";
      if(std::fabs(a-b)>8)return "SENSOR_MISMATCH";
    }
    return nullptr;
  }
  void trip(const char* why){m_=Mode::FAULT;fault_=why;armed_=false;zero();}
  void stop(){zero();armed_=false;if(m_!=Mode::FAULT)m_=Mode::OFF;}
  // This method MUST only be reachable from the physical ARM/RESET button.
  bool localArm(const Input& in,uint32_t now){
    if(unsafe(in,now))return false;
    if(m_==Mode::WORK||m_==Mode::PREHEAT)return false;
    zero();m_=Mode::OFF;fault_="NONE";armed_=true;armedMs_=now;return true;
  }
  bool start(Mode mode,float target,const Input& in,uint32_t now){
    if(mode==Mode::SLEEP){stop();if(m_!=Mode::FAULT)m_=Mode::SLEEP;return m_==Mode::SLEEP;}
    if(mode!=Mode::WORK&&mode!=Mode::PREHEAT)return false;
    if(!std::isfinite(target)||target<28||target>37)return false;
    // No remote renewal: repeated START must not reset the session deadline.
    if(!armed_||m_!=Mode::OFF||uint32_t(now-armedMs_)>60000)return false;
    if(const char* err=unsafe(in,now)){trip(err);return false;}
    armed_=false;m_=mode;target_=target;startMs_=pingMs_=now;zero();return true;
  }
  void ping(uint32_t now){if(m_==Mode::WORK||m_==Mode::PREHEAT)pingMs_=now;}
  void step(const Input& in,uint32_t now){
    uint32_t dt=ticked_?uint32_t(now-lastMs_):100;lastMs_=now;ticked_=true;
    if(armed_&&uint32_t(now-armedMs_)>60000)armed_=false;
    if(m_!=Mode::WORK&&m_!=Mode::PREHEAT){zero();return;}
    if(dt>350){trip("LOOP_STALL");return;}
    if(const char* err=unsafe(in,now)){trip(err);return;}
    if(uint32_t(now-pingMs_)>=LEASE){trip("LINK_TIMEOUT");return;}
    if(uint32_t(now-startMs_)>=(m_==Mode::PREHEAT?PREHEAT:SESSION)){stop();return;}
    out_.relay=true;
    for(int z=0;z<4;z++){
      float temp=std::max(in.c[2*z],in.c[2*z+1]);
      float error=target_-temp;
      if(error< -0.5f){out_.duty[z]=0;integ_[z]=0;continue;}
      // Bounded PI with no integral windup. Initial gains require bench tuning.
      float candidate=std::clamp(integ_[z]+0.003f*error*dt/1000.0f,0.0f,0.4f);
      float u=0.15f*error+candidate;
      if(u<1.0f)integ_[z]=candidate;
      out_.duty[z]=std::clamp(0.15f*error+integ_[z],0.0f,1.0f);
    }
  }
  bool command(const char* line,const Input& in,uint32_t now){
    if(!line||std::strlen(line)>80)return false;
    if(!std::strcmp(line,"H1 PING")){ping(now);return true;}
    if(!std::strcmp(line,"H1 STOP")){stop();return true;}
    if(!std::strcmp(line,"H1 SLEEP"))return start(Mode::SLEEP,34,in,now);
    if(!std::strcmp(line,"H1 GET"))return true;
    const char* value=nullptr;Mode mode=Mode::WORK;
    if(!std::strncmp(line,"H1 START ",9))value=line+9;
    else if(!std::strncmp(line,"H1 PREHEAT ",11)){value=line+11;mode=Mode::PREHEAT;}
    if(value){char* end=nullptr;float t=std::strtof(value,&end);if(end==value||*end)return false;return start(mode,t,in,now);}
    // ARM/RESET deliberately absent from wire protocol.
    return false;
  }
  void status(char* buf,size_t n,const Input& in)const {
    std::snprintf(buf,n,"H1 S %s %s %d %.1f %.1f %.1f %.1f %.2f %.2f %.0f %.0f %.0f %.0f\n",
      modeName(),fault_,armed_?1:0,in.c[0],in.c[2],in.c[4],in.c[6],in.batteryV,in.heaterV,
      out_.duty[0]*100,out_.duty[1]*100,out_.duty[2]*100,out_.duty[3]*100);
  }
};
}
