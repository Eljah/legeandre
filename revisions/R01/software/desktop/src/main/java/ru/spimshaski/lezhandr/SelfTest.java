package ru.spimshaski.lezhandr;
public final class SelfTest {
 static int n;
 static void check(boolean b,String s){n++;if(!b)throw new AssertionError(s);System.out.println("PASS "+s);}
 public static void run(){
  Protocol.Status s=Protocol.parse("H1 S WORK NONE 0 25.0 26.0 27.0 28.0 25.6 12.0 100 90 80 70");
  check(s.mode.equals("WORK")&&s.temperature[3]==28,"decode-status");check(s.duty[0]==100,"decode-duty");
  check(Protocol.start(34,false).equals("H1 START 34.0"),"start-frame");
  for(String line:new String[]{"","H1 S BAD X 0 1 2 3 4 25 12 0 0 0 0","H1 S WORK NONE 0 25 25 25 25 25 12 101 0 0 0","H1 S WORK NONE 0 25 25 25 25 25 12 nan 0 0 0"}){boolean rejected=false;try{Protocol.parse(line);}catch(IllegalArgumentException e){rejected=true;}check(rejected,"bad-frame-rejected");}
  for(double t:new double[]{27,38,Double.NaN,Double.POSITIVE_INFINITY}){boolean rejected=false;try{Protocol.start(t,false);}catch(IllegalArgumentException e){rejected=true;}check(rejected,"bad-target-rejected");}
  check(Double.isNaN(Protocol.parse("H1 S FAULT SENSOR 0 nan 25 25 25 25 12 0 0 0 0").temperature[0]),"nan-displayed-as-fault");
  System.out.println("TOTAL "+n+" PASS");
 }
}
