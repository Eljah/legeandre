package ru.spimshaski.lezhandr;
import java.util.concurrent.*;
import java.util.function.Predicate;
/** Integration of the actual Java transport/parser with the native MCU control core. */
public final class IntegrationTest {
 private static final BlockingQueue<Protocol.Status> q=new LinkedBlockingQueue<>();
 private static int count=0;
 private static boolean off(Protocol.Status s){for(double d:s.duty)if(d!=0)return false;return true;}
 private static Protocol.Status waitFor(String name,Predicate<Protocol.Status> p,long ms)throws Exception{
  long deadline=System.nanoTime()+TimeUnit.MILLISECONDS.toNanos(ms);Protocol.Status last=null;
  while(System.nanoTime()<deadline){last=q.poll(100,TimeUnit.MILLISECONDS);if(last!=null&&p.test(last)){System.out.println("PASS "+name);count++;return last;}}
  throw new AssertionError(name+" timed out; last="+(last==null?"none":last.mode+"/"+last.fault));
 }
 private static void send(Transport t,String s)throws Exception{q.clear();t.send(s);}
 private static Transport connect(int port)throws Exception{return Transport.tcp("127.0.0.1",port,l->{try{q.add(Protocol.parse(l));}catch(IllegalArgumentException ignored){}});}
 public static void main(String[]args)throws Exception{
  int port=args.length>0?Integer.parseInt(args[0]):18765;
  try(Transport t=connect(port)){
   waitFor("boot-is-off",s->s.mode.equals("OFF")&&off(s),3000);
   send(t,"H1 START 34");waitFor("remote-start-cannot-arm",s->s.mode.equals("OFF")&&off(s),2000);
   send(t,"SIM ARM");waitFor("physical-arm-window",s->s.armed&&off(s),2000);
   send(t,"H1 START 34");waitFor("work-reaches-real-core",s->s.mode.equals("WORK")&&s.duty[0]>0,2000);
   send(t,"H1 STOP");waitFor("stop-deenergizes",s->s.mode.equals("OFF")&&off(s)&&!s.armed,2000);
   send(t,"H1 START 34");waitFor("stop-consumes-arm",s->s.mode.equals("OFF")&&off(s),2000);
   for(String fault:new String[]{"SENSOR","FOLD","WET"}){
    send(t,"SIM CLEAR");Thread.sleep(150);send(t,"SIM ARM");waitFor("rearm-before-"+fault,s->s.armed,2000);
    send(t,"H1 START 34");waitFor("work-before-"+fault,s->s.mode.equals("WORK"),2000);
    send(t,"SIM "+fault);waitFor("fault-"+fault,s->s.mode.equals("FAULT")&&s.fault.equals(fault)&&off(s),2000);
    send(t,"H1 STOP");waitFor("fault-latched-"+fault,s->s.mode.equals("FAULT")&&off(s),2000);
   }
   send(t,"SIM CLEAR");Thread.sleep(150);send(t,"SIM ARM");waitFor("rearm-for-preheat",s->s.armed,2000);
   send(t,"H1 PREHEAT 33");waitFor("preheat-reaches-core",s->s.mode.equals("PREHEAT"),2000);
   send(t,"H1 SLEEP");waitFor("sleep-disables-heating",s->s.mode.equals("SLEEP")&&off(s),2000);
   send(t,"SIM ARM");waitFor("rearm-for-link-test",s->s.armed,2000);
   send(t,"H1 START 34");waitFor("work-before-link-loss",s->s.mode.equals("WORK"),2000);
   send(t,"H1 PING");waitFor("lost-heartbeat-safe-off",s->s.mode.equals("FAULT")&&s.fault.equals("LINK_TIMEOUT")&&off(s),7000);
  }
  q.clear();try(Transport t=connect(port)){waitFor("reconnect-starts-off",s->s.mode.equals("OFF")&&off(s),3000);}
  System.out.println("TOTAL "+count+" PASS");
 }
}
