package ru.spimshaski.lezhandr;
import android.Manifest;import android.app.*;import android.bluetooth.BluetoothDevice;import android.content.pm.PackageManager;
import android.os.*;import android.view.*;import android.widget.*;import java.util.*;
public final class MainActivity extends Activity implements BleClient.Listener{
 private BleClient ble;private TextView status,values,targetLabel;private SeekBar target;private LinearLayout devices;
 private final Set<String> seen=new HashSet<>();private final Handler handler=new Handler(Looper.getMainLooper());private long lastStatus;private boolean active;
 private final Runnable heartbeat=new Runnable(){public void run(){if(!active)return;if(ble!=null)ble.send("H1 PING");if(lastStatus>0&&System.currentTimeMillis()-lastStatus>3000)status.setText("Нет свежей телеметрии. Контроллер выключит нагрев по таймауту.");handler.postDelayed(this,1000);}};
 public void onCreate(Bundle b){super.onCreate(b);ScrollView scroll=new ScrollView(this);LinearLayout root=new LinearLayout(this);root.setOrientation(1);root.setPadding(32,48,32,32);scroll.addView(root);setContentView(scroll);
  TextView title=new TextView(this);title.setText("СПИМ С ХАСКИ\nЛЕЖАНДР");title.setTextSize(28);root.addView(title);
  status=new TextView(this);status.setText("R01 • стендовый прототип\nДля нагрева нужна физическая кнопка ARM");status.setTextSize(16);root.addView(status);
  button(root,"Найти контроллер",()->ensurePermissions());devices=new LinearLayout(this);devices.setOrientation(1);root.addView(devices);
  values=new TextView(this);values.setText("Туловище  —\nНоги  —\nСтопы  —\nРуки  —");values.setTextSize(23);values.setPadding(0,32,0,32);root.addView(values);
  targetLabel=new TextView(this);targetLabel.setText("Цель: 34 °C");root.addView(targetLabel);target=new SeekBar(this);target.setMax(9);target.setProgress(6);target.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener(){public void onProgressChanged(SeekBar s,int p,boolean user){targetLabel.setText("Цель: "+(28+p)+" °C");}public void onStartTrackingTouch(SeekBar s){}public void onStopTrackingTouch(SeekBar s){}});root.addView(target);
  button(root,"Работа • до 30 минут",()->send(Protocol.start(28+target.getProgress(),false)));
  button(root,"Предварительный прогрев • 10 минут",()->send(Protocol.start(28+target.getProgress(),true)));
  button(root,"Сон • без нагрева",()->send("H1 SLEEP"));button(root,"СТОП",()->send("H1 STOP"));
  TextView safety=new TextView(this);safety.setText("Приложение не может сбросить аппаратную аварию. При уходе приложения в фон нагрев останавливается. Не использовать R01 на человеке до испытаний.");safety.setPadding(0,24,0,0);root.addView(safety);
 }
 private void button(LinearLayout l,String s,Runnable run){Button b=new Button(this);b.setText(s);b.setOnClickListener(v->run.run());l.addView(b,new LinearLayout.LayoutParams(-1,-2));}
 private void send(String s){if(ble!=null)ble.send(s);}
 private void ensurePermissions(){
  String[]permissions=Build.VERSION.SDK_INT>=31?new String[]{Manifest.permission.BLUETOOTH_SCAN,Manifest.permission.BLUETOOTH_CONNECT}:new String[]{Manifest.permission.ACCESS_FINE_LOCATION};
  for(String p:permissions)if(checkSelfPermission(p)!=PackageManager.PERMISSION_GRANTED){requestPermissions(permissions,10);return;}
  if(ble!=null)ble.close();ble=new BleClient(this,this);seen.clear();devices.removeAllViews();ble.scan();
 }
 public void onRequestPermissionsResult(int request,String[]p,int[]r){super.onRequestPermissionsResult(request,p,r);if(request==10){for(int result:r)if(result!=PackageManager.PERMISSION_GRANTED){error("Разрешения Bluetooth не выданы");return;}ensurePermissions();}}
 @android.annotation.SuppressLint("MissingPermission") public void device(BluetoothDevice d){if(!seen.add(d.getAddress()))return;String name=d.getName();button(devices,(name==null?"Лежандр":name)+"\n"+d.getAddress(),()->ble.connect(d));}
 public void ready(){status.setText("BLE подключён. Удерживайте ARM на контроллере перед запуском.");}
 public void error(String s){status.setText(s);}
 public void line(String line){try{Protocol.Status s=Protocol.parse(line);lastStatus=System.currentTimeMillis();status.setText(s.mode+" • "+s.fault+" • "+(s.armed?"ARM готов":"ARM не активен"));String[]names={"Туловище","Ноги","Стопы","Руки"};StringBuilder out=new StringBuilder();for(int i=0;i<4;i++)out.append(String.format(Locale.ROOT,"%s: %.1f °C / %.0f %%\n",names[i],s.temperature[i],s.duty[i]));out.append(String.format(Locale.ROOT,"Батарея: %.2f V",s.battery));values.setText(out.toString());}catch(Exception e){error("Неверная телеметрия");}}
 protected void onStart(){super.onStart();active=true;handler.post(heartbeat);}
 protected void onStop(){send("H1 STOP");active=false;handler.removeCallbacks(heartbeat);super.onStop();}
 protected void onDestroy(){if(ble!=null)ble.close();handler.removeCallbacksAndMessages(null);super.onDestroy();}
}
