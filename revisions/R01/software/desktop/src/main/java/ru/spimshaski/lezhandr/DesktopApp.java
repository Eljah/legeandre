package ru.spimshaski.lezhandr;
import javax.swing.*;import javax.swing.border.*;import java.awt.*;import java.awt.event.*;import java.awt.image.BufferedImage;
import javax.imageio.ImageIO;import java.io.*;import java.nio.file.*;import java.util.*;import java.util.concurrent.*;
public final class DesktopApp extends JFrame{
 private final JComboBox<String> source=new JComboBox<>(new String[]{"DEMO / Java UI model","TCP / native firmware core","USB / actual controller"});
 private final JTextField address=new JTextField("127.0.0.1:8765",18);
 private final JLabel state=new JLabel("Нет подключения"),limits=new JLabel("Сначала физическая кнопка ARM. Сон: нагрев выключен.");
 private final JTextArea log=new JTextArea(7,70);
 private final JSlider target=new JSlider(28,37,34);
 private final JLabel targetLabel=new JLabel("Цель 34 °C");
 private final JLabel[] zone=new JLabel[4];private final JProgressBar[] bars=new JProgressBar[4];
 private final Plot plot=new Plot();private volatile Transport transport;private volatile long lastRx;
 private final java.util.List<String> history=new ArrayList<>();
 private final ScheduledExecutorService worker=Executors.newSingleThreadScheduledExecutor(r->{Thread t=new Thread(r,"heartbeat");t.setDaemon(true);return t;});
 public DesktopApp(){
  super("Спим с хаски • ЛЕЖАНДР R01");setDefaultCloseOperation(DO_NOTHING_ON_CLOSE);
  JPanel root=new JPanel(new BorderLayout(16,16));root.setBorder(new EmptyBorder(20,24,20,24));setContentPane(root);
  JPanel top=new JPanel(new BorderLayout(4,10));JLabel title=new JLabel("СПИМ С ХАСКИ  /  ЛЕЖАНДР");title.setFont(title.getFont().deriveFont(Font.BOLD,26));top.add(title,BorderLayout.NORTH);
  JPanel connection=new JPanel(new FlowLayout(FlowLayout.LEFT));connection.add(source);connection.add(address);JButton connect=new JButton("Подключить");connect.addActionListener(e->connect());connection.add(connect);top.add(connection,BorderLayout.CENTER);
  state.setFont(state.getFont().deriveFont(Font.BOLD,16));top.add(state,BorderLayout.SOUTH);root.add(top,BorderLayout.NORTH);
  JPanel center=new JPanel(new BorderLayout(12,12));JPanel zones=new JPanel(new GridLayout(1,4,12,12));String[]names={"Туловище","Ноги","Стопы","Руки"};
  for(int i=0;i<4;i++){JPanel p=new JPanel(new BorderLayout(8,8));p.setBorder(BorderFactory.createTitledBorder(names[i]));zone[i]=new JLabel("— °C",SwingConstants.CENTER);zone[i].setFont(zone[i].getFont().deriveFont(Font.BOLD,28));bars[i]=new JProgressBar(0,100);bars[i].setStringPainted(true);p.add(zone[i],BorderLayout.CENTER);p.add(bars[i],BorderLayout.SOUTH);zones.add(p);}
  center.add(zones,BorderLayout.NORTH);plot.setPreferredSize(new Dimension(850,170));center.add(plot,BorderLayout.CENTER);
  JPanel controls=new JPanel(new GridLayout(3,1,6,6));JPanel set=new JPanel(new FlowLayout(FlowLayout.LEFT));target.setMajorTickSpacing(1);target.setPaintTicks(true);target.setPaintLabels(true);target.addChangeListener(e->targetLabel.setText("Цель "+target.getValue()+" °C"));set.add(targetLabel);set.add(target);controls.add(set);
  JPanel buttons=new JPanel(new FlowLayout(FlowLayout.LEFT));button(buttons,"Работа",()->send(Protocol.start(target.getValue(),false)));button(buttons,"Прогрев 10 мин",()->send(Protocol.start(target.getValue(),true)));button(buttons,"Сон без нагрева",()->send("H1 SLEEP"));JButton stop=button(buttons,"СТОП",()->send("H1 STOP"));stop.setFont(stop.getFont().deriveFont(Font.BOLD));controls.add(buttons);
  JPanel tests=new JPanel(new FlowLayout(FlowLayout.LEFT));tests.add(new JLabel("Только симулятор:"));button(tests,"ARM",()->sim("SIM ARM"));button(tests,"Обрыв NTC",()->sim("SIM SENSOR"));button(tests,"Намокание",()->sim("SIM WET"));button(tests,"Складывание",()->sim("SIM FOLD"));controls.add(tests);center.add(controls,BorderLayout.SOUTH);root.add(center,BorderLayout.CENTER);
  JPanel bottom=new JPanel(new BorderLayout(6,6));bottom.add(limits,BorderLayout.NORTH);log.setEditable(false);log.setFont(new Font(Font.MONOSPACED,Font.PLAIN,11));bottom.add(new JScrollPane(log),BorderLayout.CENTER);JPanel file=new JPanel(new FlowLayout(FlowLayout.LEFT));button(file,"Экспорт CSV",this::exportCsv);file.add(new JLabel("R01: стендовый образец. Приложение не заменяет аппаратную защиту."));bottom.add(file,BorderLayout.SOUTH);root.add(bottom,BorderLayout.SOUTH);
  addWindowListener(new WindowAdapter(){public void windowClosing(WindowEvent e){send("H1 STOP");disconnect();worker.shutdownNow();dispose();}});
  worker.scheduleAtFixedRate(()->{if(transport!=null){send("H1 PING");if(lastRx>0&&System.currentTimeMillis()-lastRx>3000)SwingUtilities.invokeLater(()->state.setText("Нет свежей телеметрии — проверьте контроллер"));}},1,1,TimeUnit.SECONDS);
  setSize(1050,800);setLocationRelativeTo(null);
 }
 private static JButton button(JPanel panel,String name,Runnable task){JButton b=new JButton(name);b.addActionListener(e->task.run());panel.add(b);return b;}
 private void disconnect(){Transport t=transport;transport=null;if(t!=null)t.close();lastRx=0;}
 private void connect(){
  disconnect();int kind=source.getSelectedIndex();String text=address.getText().trim();
  worker.execute(()->{try{
   Transport t=kind==0?new DemoTransport(this::received):kind==1?Transport.tcp(text.split(":")[0],Integer.parseInt(text.split(":")[1]),this::received):Transport.usb(text,this::received);
   transport=t;send("H1 GET");SwingUtilities.invokeLater(()->append("CONNECT "+source.getItemAt(kind)));
  }catch(Exception e){SwingUtilities.invokeLater(()->{state.setText("Ошибка подключения");append(e.toString());});}});
 }
 private void sim(String command){if(source.getSelectedIndex()==2){append("SIM-команды запрещены для USB. Нажмите физическую кнопку.");return;}send(command);}
 private void send(String command){Transport t=transport;if(t==null)return;try{t.send(command);}catch(Exception e){SwingUtilities.invokeLater(()->append("TX error: "+e.getMessage()));}}
 private void received(String line){
  if(!line.startsWith("H1 S ")){SwingUtilities.invokeLater(()->append(line));return;}
  try{Protocol.Status s=Protocol.parse(line);lastRx=System.currentTimeMillis();SwingUtilities.invokeLater(()->{
   state.setText(s.mode+"   /   "+(s.armed?"ARM готов":"ARM не активен")+"   /   батарея "+String.format(Locale.ROOT,"%.2f",s.battery)+" V   /   "+s.fault);
   for(int i=0;i<4;i++){zone[i].setText(Double.isFinite(s.temperature[i])?String.format(Locale.ROOT,"%.1f °C",s.temperature[i]):"ОБРЫВ");bars[i].setValue((int)s.duty[i]);}
   plot.add(s.temperature);history.add(System.currentTimeMillis()+","+line.replace(' ',','));if(history.size()>20000)history.remove(0);append(line);
  });}catch(Exception e){SwingUtilities.invokeLater(()->append("Invalid telemetry: "+line));}
 }
 private void append(String t){log.append(t+"\n");if(log.getLineCount()>120)log.setText(log.getText().substring(log.getText().indexOf('\n')+1));log.setCaretPosition(log.getDocument().getLength());}
 private void exportCsv(){JFileChooser c=new JFileChooser();c.setSelectedFile(new File("lezhandr-telemetry.csv"));if(c.showSaveDialog(this)==JFileChooser.APPROVE_OPTION){try{Files.write(c.getSelectedFile().toPath(),history);append("CSV: "+c.getSelectedFile());}catch(IOException e){append(e.toString());}}}
 private static final class Plot extends JPanel{
  private final java.util.List<double[]> data=new ArrayList<>();
  void add(double[]t){data.add(t.clone());if(data.size()>180)data.remove(0);repaint();}
  protected void paintComponent(Graphics g){super.paintComponent(g);Graphics2D p=(Graphics2D)g.create();p.setRenderingHint(RenderingHints.KEY_ANTIALIASING,RenderingHints.VALUE_ANTIALIAS_ON);int w=getWidth(),h=getHeight();p.setColor(new Color(230,235,239));p.fillRoundRect(0,0,w,h,16,16);p.setColor(Color.DARK_GRAY);p.drawString("Температура • последние 90 секунд • 15–42 °C",12,20);
   Color[]colors={new Color(30,90,120),new Color(60,135,105),new Color(160,110,45),new Color(155,70,90)};
   for(int z=0;z<4;z++){p.setColor(colors[z]);for(int i=1;i<data.size();i++){double a=data.get(i-1)[z],b=data.get(i)[z];if(Double.isFinite(a)&&Double.isFinite(b)){int x1=40+(i-1)*(w-60)/180,x2=40+i*(w-60)/180,y1=h-20-(int)((a-15)*(h-55)/27),y2=h-20-(int)((b-15)*(h-55)/27);p.drawLine(x1,y1,x2,y2);}}}p.dispose();
  }
 }
 public static void main(String[] args)throws Exception{
  if(args.length>0&&args[0].equals("--self-test")){SelfTest.run();return;}
  UIManager.setLookAndFeel(UIManager.getCrossPlatformLookAndFeelClassName());
  SwingUtilities.invokeLater(()->{DesktopApp a=new DesktopApp();a.setVisible(true);
   if(args.length>0&&args[0].startsWith("--screenshot=")){String file=args[0].substring(13);a.connect();javax.swing.Timer one=new javax.swing.Timer(800,e->{a.sim("SIM ARM");a.send("H1 START 34");});one.setRepeats(false);one.start();
    javax.swing.Timer shot=new javax.swing.Timer(3500,e->{try{BufferedImage im=new BufferedImage(a.getWidth(),a.getHeight(),BufferedImage.TYPE_INT_RGB);Graphics2D g=im.createGraphics();a.paint(g);g.dispose();ImageIO.write(im,"png",new File(file));a.disconnect();a.worker.shutdownNow();a.dispose();}catch(Exception x){x.printStackTrace();System.exit(1);}});shot.setRepeats(false);shot.start();
   }
  });
 }
}
