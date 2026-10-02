package ru.spimshaski.lezhandr;
import java.io.*;import java.net.*;import java.nio.charset.StandardCharsets;import java.util.function.Consumer;
public interface Transport extends AutoCloseable {
 void send(String line)throws Exception;
 void close();
 static Transport tcp(String host,int port,Consumer<String> sink)throws Exception{
  if(!host.equals("127.0.0.1")&&!host.equals("localhost"))throw new IllegalArgumentException("R01 simulator accepts loopback only");
  Socket s=new Socket();s.connect(new InetSocketAddress(host,port),2000);
  return new StreamTransport(s.getInputStream(),s.getOutputStream(),s,sink);
 }
 static Transport usb(String port,Consumer<String> sink)throws Exception{
  // Reflection keeps the offline demo JAR runnable without native library downloads.
  Class<?> c;
  try{c=Class.forName("com.fazecast.jSerialComm.SerialPort");}
  catch(ClassNotFoundException e){throw new IOException("USB requires jSerialComm. Build the Maven shaded JAR (mvn package), or add jSerialComm to classpath.");}
  Object p=c.getMethod("getCommPort",String.class).invoke(null,port);
  c.getMethod("setComPortParameters",int.class,int.class,int.class,int.class).invoke(p,115200,8,1,0);
  c.getMethod("setComPortTimeouts",int.class,int.class,int.class).invoke(p,16,1000,1000);
  if(!Boolean.TRUE.equals(c.getMethod("openPort").invoke(p)))throw new IOException("Cannot open "+port);
  InputStream in=(InputStream)c.getMethod("getInputStream").invoke(p);
  OutputStream out=(OutputStream)c.getMethod("getOutputStream").invoke(p);
  return new StreamTransport(in,out,()->{try{c.getMethod("closePort").invoke(p);}catch(Exception ignored){}},sink);
 }
}
final class StreamTransport implements Transport{
 private final InputStream input;private final OutputStream output;private final AutoCloseable resource;private volatile boolean closed;
 StreamTransport(InputStream i,OutputStream o,AutoCloseable r,Consumer<String> sink){
  input=i;output=o;resource=r;
  Thread t=new Thread(()->{
   try{StringBuilder b=new StringBuilder();boolean discard=false;int c;
    while(!closed&&(c=input.read())!=-1){
     if(c=='\r')continue;
     if(c=='\n'){if(!discard)sink.accept(b.toString());b.setLength(0);discard=false;}
     else if(!discard){if(b.length()>=256){discard=true;b.setLength(0);}else b.append((char)c);}
    }
    if(!closed)sink.accept("ERROR disconnected");
   }catch(Exception e){if(!closed)sink.accept("ERROR "+e.getMessage());}
  },"husky-reader");t.setDaemon(true);t.start();
 }
 public synchronized void send(String l)throws IOException{
  if(closed)throw new IOException("Closed");if(l.length()>80||l.indexOf('\n')>=0)throw new IOException("Command frame");
  output.write((l+"\n").getBytes(StandardCharsets.US_ASCII));output.flush();
 }
 public void close(){closed=true;try{input.close();}catch(Exception ignored){}try{output.close();}catch(Exception ignored){}try{resource.close();}catch(Exception ignored){}}
}
