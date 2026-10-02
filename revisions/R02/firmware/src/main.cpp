/* R01 BENCH FIRMWARE ONLY. Physical thermostat/relay/watchdog chain required.
 * Never use software limits as the sole protection for a person.
 */
#include <Arduino.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include <BLESecurity.h>
#include <esp_task_wdt.h>
#include <esp_arduino_version.h>
#include "ControlCore.hpp"
using namespace husky;
constexpr int NTC[8]={1,2,4,5,6,7,8,9},PWM[4]={12,13,14,15};
constexpr int BAT_ADC=10,H12_ADC=11,ARM=16,FOLD=17,WET=18,LOOP=21,PERMIT=40,WD=41;
constexpr char SERVICE[]="f8720001-7649-4a9f-bd4e-11ee30c01001";
constexpr char RX[]="f8720002-7649-4a9f-bd4e-11ee30c01001";
constexpr char TX[]="f8720003-7649-4a9f-bd4e-11ee30c01001";
Controller ctl; Input input; BLECharacteristic* tx=nullptr;
volatile bool authenticated=false,connected=false;volatile uint32_t pairUntil=0;
uint32_t passkey=0; QueueHandle_t commands;
struct Command{char text[81];};
// BLE callbacks only enqueue; controller state belongs to the main task.
class Rx: public BLECharacteristicCallbacks{
 void onWrite(BLECharacteristic* ch)override{
  if(!authenticated)return;auto v=ch->getValue();const char* p=v.c_str();
  size_t n=std::strlen(p);if(!n||n>80)return;
  Command c{};std::memcpy(c.text,p,n);while(n&&(c.text[n-1]=='\n'||c.text[n-1]=='\r'))c.text[--n]=0;
  xQueueSend(commands,&c,0);
 }
};
class Server:public BLEServerCallbacks{
 void onConnect(BLEServer*)override{connected=true;authenticated=false;}
 void onDisconnect(BLEServer*)override{connected=false;authenticated=false;BLEDevice::startAdvertising();}
};
class Security:public BLESecurityCallbacks{
 uint32_t onPassKeyRequest()override{return passkey;}
 void onPassKeyNotify(uint32_t n)override{Serial.printf("DBG PAIR PIN %06lu\n",(unsigned long)n);}
 bool onConfirmPIN(uint32_t)override{return false;}
 bool onSecurityRequest()override{return int32_t(pairUntil-millis())>0;}
 void onAuthenticationComplete(esp_ble_auth_cmpl_t c)override{authenticated=c.success;}
};
float ntc(int pin){
 // Divider: 3.3 V -- 10k 1% -- ADC -- 10k B3950 NTC -- GND.
 float mv=0;for(int i=0;i<8;i++)mv+=analogReadMilliVolts(pin);mv/=8;
 if(mv<80||mv>3050)return NAN; // open/short and rail clipping fail closed
 const float r=10000.0f*mv/(3300.0f-mv);
 return 1.0f/(1.0f/298.15f+logf(r/10000.0f)/3950.0f)-273.15f;
}
void outputs(){
 bool enable=ctl.output().relay;
 // Drop common permit before changing gates on a fault.
 if(!enable)digitalWrite(PERMIT,LOW);
 for(int z=0;z<4;z++){
  uint32_t duty=enable?uint32_t(ctl.output().duty[z]*1023):0;
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  ledcWrite(PWM[z],duty);
#else
  ledcWrite(z,duty);
#endif
 }
 if(enable)digitalWrite(PERMIT,HIGH);
}
void setup(){
 pinMode(PERMIT,OUTPUT);digitalWrite(PERMIT,LOW);pinMode(WD,OUTPUT);digitalWrite(WD,LOW);
 for(int z=0;z<4;z++){
  pinMode(PWM[z],OUTPUT);digitalWrite(PWM[z],LOW);
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  ledcAttach(PWM[z],1000,10);ledcWrite(PWM[z],0);
#else
  ledcSetup(z,1000,10);ledcAttachPin(PWM[z],z);ledcWrite(z,0);
#endif
 }
 Serial.begin(115200);analogReadResolution(12);analogSetAttenuation(ADC_11db);
 for(int p:{ARM,FOLD,WET,LOOP})pinMode(p,INPUT_PULLUP);
 commands=xQueueCreate(8,sizeof(Command));
 passkey=100000+(uint32_t(ESP.getEfuseMac()>>16)%900000); // prototype unique printed PIN; not a production secret
 BLEDevice::init("Husky-Lezhandr-R01");BLEDevice::setEncryptionLevel(ESP_BLE_SEC_ENCRYPT_MITM);
 BLEDevice::setSecurityCallbacks(new Security());
 auto sec=new BLESecurity();sec->setAuthenticationMode(ESP_LE_AUTH_REQ_SC_MITM_BOND);
 sec->setCapability(ESP_IO_CAP_OUT);sec->setStaticPIN(passkey);
 auto server=BLEDevice::createServer();server->setCallbacks(new Server());auto svc=server->createService(SERVICE);
 auto rx=svc->createCharacteristic(RX,BLECharacteristic::PROPERTY_WRITE);
 rx->setAccessPermissions(ESP_GATT_PERM_WRITE_ENC_MITM);rx->setCallbacks(new Rx());
 tx=svc->createCharacteristic(TX,BLECharacteristic::PROPERTY_NOTIFY|BLECharacteristic::PROPERTY_READ);
 tx->setAccessPermissions(ESP_GATT_PERM_READ_ENC_MITM);tx->addDescriptor(new BLE2902());
 svc->start();BLEDevice::getAdvertising()->addServiceUUID(SERVICE);BLEDevice::startAdvertising();
#if ESP_ARDUINO_VERSION_MAJOR >= 3
 esp_task_wdt_config_t cfg={.timeout_ms=2000,.idle_core_mask=0,.trigger_panic=true};esp_task_wdt_init(&cfg);
#else
 esp_task_wdt_init(2,true);
#endif
 esp_task_wdt_add(nullptr);
 Serial.println("DBG R01 BENCH ONLY. Hold physical ARM for 2 seconds; outputs remain OFF until START.");
}
void loop(){
 static uint32_t prev=0,report=0,press=0;static bool wasPressed=false,acted=false,beat=false;
 static char serial[81];static size_t used=0;static bool discard=false;
 uint32_t now=millis();
 while(Serial.available()){
  char c=char(Serial.read());
  if(c=='\r')continue;
  if(c=='\n'){if(!discard&&used){serial[used]=0;ctl.command(serial,input,now);}used=0;discard=false;}
  else if(!discard){if(used<80)serial[used++]=c;else{discard=true;used=0;}}
 }
 Command cmd{};while(xQueueReceive(commands,&cmd,0)==pdTRUE)ctl.command(cmd.text,input,now);
 if(uint32_t(now-prev)<100){delay(2);return;}prev=now;
 for(int i=0;i<8;i++)input.c[i]=ntc(NTC[i]);
 input.batteryV=analogReadMilliVolts(BAT_ADC)*11.0f/1000.0f; // 100k / 10k divider
 input.heaterV=analogReadMilliVolts(H12_ADC)*5.7f/1000.0f;  // 47k / 10k divider
 input.deployed=digitalRead(FOLD)==LOW;input.dry=digitalRead(WET)==LOW;input.safetyLoop=digitalRead(LOOP)==LOW;
 input.sampledMs=now;
 bool pressed=digitalRead(ARM)==LOW;
 if(pressed&&!wasPressed){press=now;acted=false;}
 if(pressed&&!acted&&uint32_t(now-press)>2000){
  acted=true;if(ctl.localArm(input,now)){pairUntil=now+60000;Serial.printf("DBG LOCAL ARM; PAIR PIN %06lu\n",(unsigned long)passkey);}
 }
 wasPressed=pressed;ctl.step(input,now);outputs();
 // Heartbeat generated here, NOT by a timer ISR. A stalled control task must stop the external watchdog.
 beat=!beat;digitalWrite(WD,beat);esp_task_wdt_reset();
 if(uint32_t(now-report)>=1000){
  report=now;char status[192];ctl.status(status,sizeof status,input);Serial.print(status);
  if(connected&&authenticated){ // 20-byte notification chunks work even before an MTU exchange.
   size_t n=std::strlen(status);for(size_t i=0;i<n;i+=20){tx->setValue((uint8_t*)status+i,std::min(size_t(20),n-i));tx->notify();delay(3);}
  }
 }
}
