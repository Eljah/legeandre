package ru.spimshaski.lezhandr;
import java.util.*;import java.util.concurrent.*;import java.util.function.Consumer;
/** UI-only Java plant. Native TCP simulator executes the real firmware ControlCore.hpp. */
public final class DemoTransport implements Transport{
 private final ScheduledExecutorService worker=Executors.newSingleThreadScheduledExecutor(r->{Thread t=new Thread(r,"husky-demo");t.setDaemon(true);return t;});
 private final Consumer<String> sink;private final double[]t={25,25,25,25},d=new double[4];
 private String mode="OFF",fault="NONE";private boolean armed;private long ping,start,arm;private double target=34;
 public DemoTransport(Consumer<String>s){sink=s;worker.scheduleAtFixedRate(this::tick,0,500,TimeUnit.MILLISECONDS);}
 public synchronized void send(String command){
  long now=System.nanoTime()/1000000;
  if(command.equals("SIM ARM")){mode="OFF";fault="NONE";armed=true;arm=now;Arrays.fill(t,25);Arrays.fill(d,0);}
  else if(command.equals("SIM SENSOR")){fault("SENSOR");t[0]=Double.NaN;}
  else if(command.equals("SIM WET"))fault("WET");
  else if(command.equals("SIM FOLD"))fault("FOLD");
  else if(command.equals("H1 STOP")){if(!mode.equals("FAULT"))mode="OFF";armed=false;Arrays.fill(d,0);}
  else if(command.equals("H1 SLEEP")){if(!mode.equals("FAULT"))mode="SLEEP";armed=false;Arrays.fill(d,0);}
  else if(command.equals("H1 PING"))ping=now;
  else if(command.startsWith("H1 START ")||command.startsWith("H1 PREHEAT ")){
   try{double set=Double.parseDouble(command.substring(command.lastIndexOf(' ')+1));
    if(armed&&mode.equals("OFF")&&now-arm<=60000&&Double.isFinite(set)&&set>=28&&set<=37){armed=false;target=set;mode=command.contains("PREHEAT")?"PREHEAT":"WORK";start=ping=now;}
   }catch(NumberFormatException ignored){}
  }
 }
 private void fault(String why){mode="FAULT";fault=why;armed=false;Arrays.fill(d,0);}
 private synchronized void tick(){
  long now=System.nanoTime()/1000000;if(armed&&now-arm>60000)armed=false;
  boolean active=mode.equals("WORK")||mode.equals("PREHEAT");
  if(active&&now-ping>=5000){fault("LINK_TIMEOUT");active=false;}
  if(active&&now-start>=(mode.equals("PREHEAT")?600000:1800000)){mode="OFF";armed=false;active=false;}
  for(int i=0;i<4;i++){d[i]=active?Math.max(0,Math.min(100,(target-t[i])*15)):0;if(Double.isFinite(t[i]))t[i]+=.5*(.09*d[i]/100-.003*(t[i]-20));}
  sink.accept(String.format(Locale.ROOT,"H1 S %s %s %d %.1f %.1f %.1f %.1f 25.60 12.00 %.0f %.0f %.0f %.0f",mode,fault,armed?1:0,t[0],t[1],t[2],t[3],d[0],d[1],d[2],d[3]));
 }
 public void close(){worker.shutdownNow();}
}
