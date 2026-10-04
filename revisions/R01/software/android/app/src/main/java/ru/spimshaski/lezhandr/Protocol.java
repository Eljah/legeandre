package ru.spimshaski.lezhandr;
import java.util.Locale;
/** ASCII line protocol H1; malformed telemetry must never look like valid status. */
public final class Protocol {
 private Protocol(){}
 public static final class Status {
  public final String mode,fault;public final boolean armed;
  public final double[] temperature,duty;public final double battery,heater;
  Status(String m,String f,boolean a,double[]t,double[]d,double b,double h){mode=m;fault=f;armed=a;temperature=t;duty=d;battery=b;heater=h;}
 }
 public static Status parse(String line){
  if(line==null||line.length()>256)throw new IllegalArgumentException("Frame length");
  String[] p=line.trim().split(" +");
  if(p.length!=15||!p[0].equals("H1")||!p[1].equals("S"))throw new IllegalArgumentException("Not H1 status");
  if(!p[2].matches("OFF|WORK|PREHEAT|SLEEP|FAULT")||!p[4].matches("[01]"))throw new IllegalArgumentException("State");
  double[]t=new double[4],d=new double[4];
  for(int i=0;i<4;i++){t[i]=number(p[5+i],true);d[i]=number(p[11+i],false);if(d[i]<0||d[i]>100)throw new IllegalArgumentException("Duty");}
  return new Status(p[2],p[3],p[4].equals("1"),t,d,number(p[9],true),number(p[10],true));
 }
 private static double number(String v,boolean allowNan){
  double n=v.equalsIgnoreCase("nan")?Double.NaN:Double.parseDouble(v);
  if(Double.isInfinite(n)||(!allowNan&&!Double.isFinite(n)))throw new IllegalArgumentException("Nonfinite");return n;
 }
 public static String start(double t,boolean preheat){
  if(!Double.isFinite(t)||t<28||t>37)throw new IllegalArgumentException("Target 28..37 C");
  return String.format(Locale.ROOT,preheat?"H1 PREHEAT %.1f":"H1 START %.1f",t);
 }
}
