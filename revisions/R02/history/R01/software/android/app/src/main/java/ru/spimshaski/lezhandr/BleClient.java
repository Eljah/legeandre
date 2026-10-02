package ru.spimshaski.lezhandr;
import android.Manifest;import android.annotation.SuppressLint;import android.bluetooth.*;import android.bluetooth.le.*;
import android.content.*;import android.os.*;import java.util.*;import java.nio.charset.StandardCharsets;
/** One GATT operation at a time, bounded frames and queue, encrypted paired device. */
@SuppressLint("MissingPermission")
public final class BleClient implements AutoCloseable{
 public interface Listener{void device(BluetoothDevice d);void line(String s);void error(String s);void ready();}
 public static final UUID SERVICE=UUID.fromString("f8720001-7649-4a9f-bd4e-11ee30c01001");
 private static final UUID RX=UUID.fromString("f8720002-7649-4a9f-bd4e-11ee30c01001"),TX=UUID.fromString("f8720003-7649-4a9f-bd4e-11ee30c01001"),CCCD=UUID.fromString("00002902-0000-1000-8000-00805f9b34fb");
 private final Context context;private final Listener listener;private final Handler main=new Handler(Looper.getMainLooper());
 private final BluetoothAdapter adapter;private BluetoothGatt gatt;private BluetoothGattCharacteristic rx;
 private final ArrayDeque<byte[]> queue=new ArrayDeque<>();private boolean busy,usable,closed,scanning;
 private final StringBuilder frame=new StringBuilder();private boolean discard;
 private BroadcastReceiver bondReceiver;private BluetoothDevice selected;
 private final ScanCallback scan=new ScanCallback(){
  public void onScanResult(int type,ScanResult result){main.post(()->listener.device(result.getDevice()));}
  public void onScanFailed(int code){main.post(()->listener.error("BLE scan error "+code));}
 };
 public BleClient(Context c,Listener l){context=c.getApplicationContext();listener=l;adapter=((BluetoothManager)c.getSystemService(Context.BLUETOOTH_SERVICE)).getAdapter();}
 public void scan(){
  if(adapter==null||!adapter.isEnabled()){listener.error("Включите Bluetooth");return;}
  stopScan();scanning=true;adapter.getBluetoothLeScanner().startScan(Collections.singletonList(new ScanFilter.Builder().setServiceUuid(new ParcelUuid(SERVICE)).build()),new ScanSettings.Builder().setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY).build(),scan);
  main.postDelayed(this::stopScan,12000);
 }
 public void stopScan(){if(scanning&&adapter!=null&&adapter.getBluetoothLeScanner()!=null)adapter.getBluetoothLeScanner().stopScan(scan);scanning=false;}
 public void connect(BluetoothDevice d){
  stopScan();selected=d;closed=false;
  if(d.getBondState()==BluetoothDevice.BOND_BONDED){connectBonded(d);return;}
  listener.error("На контроллере удерживайте ARM 2 с. Введите PIN с USB-консоли/этикетки прототипа.");
  bondReceiver=new BroadcastReceiver(){public void onReceive(Context c,Intent i){
   BluetoothDevice x=i.getParcelableExtra(BluetoothDevice.EXTRA_DEVICE);
   if(x==null||selected==null||!x.getAddress().equals(selected.getAddress()))return;
   int state=i.getIntExtra(BluetoothDevice.EXTRA_BOND_STATE,BluetoothDevice.BOND_NONE);
   if(state==BluetoothDevice.BOND_BONDED){unregisterBond();connectBonded(x);}
   else if(state==BluetoothDevice.BOND_NONE){unregisterBond();listener.error("Сопряжение не завершено");}
  }};
  IntentFilter filter=new IntentFilter(BluetoothDevice.ACTION_BOND_STATE_CHANGED);
  if(Build.VERSION.SDK_INT>=33)context.registerReceiver(bondReceiver,filter,Context.RECEIVER_EXPORTED);else context.registerReceiver(bondReceiver,filter);
  if(!d.createBond()){unregisterBond();listener.error("Не удалось начать сопряжение");}
 }
 private void unregisterBond(){if(bondReceiver!=null){try{context.unregisterReceiver(bondReceiver);}catch(Exception ignored){}bondReceiver=null;}}
 private void connectBonded(BluetoothDevice d){if(gatt!=null)gatt.close();gatt=d.connectGatt(context,false,callback,BluetoothDevice.TRANSPORT_LE);}
 private final BluetoothGattCallback callback=new BluetoothGattCallback(){
  public void onConnectionStateChange(BluetoothGatt g,int status,int state){main.post(()->{
   if(status!=BluetoothGatt.GATT_SUCCESS||state==BluetoothProfile.STATE_DISCONNECTED){usable=false;busy=false;queue.clear();listener.error("BLE отключён: "+status);return;}
   if(state==BluetoothProfile.STATE_CONNECTED&&!g.discoverServices())listener.error("Не удалось запросить службы");
  });}
  public void onServicesDiscovered(BluetoothGatt g,int status){main.post(()->{
   BluetoothGattService s=g.getService(SERVICE);if(status!=0||s==null){listener.error("Служба Лежандр отсутствует");return;}
   rx=s.getCharacteristic(RX);BluetoothGattCharacteristic tx=s.getCharacteristic(TX);
   if(rx==null||tx==null){listener.error("Неверная схема GATT");return;}
   BluetoothGattDescriptor descriptor=tx.getDescriptor(CCCD);if(descriptor==null){listener.error("CCCD отсутствует");return;}
   g.setCharacteristicNotification(tx,true);descriptor.setValue(BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE);
   if(!g.writeDescriptor(descriptor))listener.error("Не удалось включить уведомления");
  });}
  public void onDescriptorWrite(BluetoothGatt g,BluetoothGattDescriptor d,int status){main.post(()->{
   if(status!=0){listener.error("Нет защищённого доступа: "+status);return;}
   usable=true;listener.ready();send("H1 GET");
  });}
  public void onCharacteristicChanged(BluetoothGatt g,BluetoothGattCharacteristic c){byte[]v=c.getValue();if(v!=null)main.post(()->consume(v));}
  public void onCharacteristicChanged(BluetoothGatt g,BluetoothGattCharacteristic c,byte[]value){byte[]v=value.clone();main.post(()->consume(v));}
  public void onCharacteristicWrite(BluetoothGatt g,BluetoothGattCharacteristic c,int status){main.post(()->{
   busy=false;if(status!=0){queue.clear();listener.error("Команда не подтверждена: "+status);}else pump();
  });}
 };
 private void consume(byte[] data){for(byte b:data){char c=(char)(b&255);if(c=='\r')continue;
  if(c=='\n'){if(!discard)listener.line(frame.toString());frame.setLength(0);discard=false;}
  else if(!discard){if(frame.length()>=256){frame.setLength(0);discard=true;listener.error("Слишком длинная телеметрия");}else frame.append(c);}
 }}
 public void send(String command){
  if(!usable||closed)return;byte[]b=command.getBytes(StandardCharsets.US_ASCII);
  // Commands kept <=20 bytes: works at default ATT MTU 23 without fragmentation.
  if(b.length>20||command.contains("\n")){listener.error("Длина команды");return;}
  if(queue.size()>=8){listener.error("Очередь BLE заполнена");return;}queue.add(b);pump();
 }
 private void pump(){if(busy||queue.isEmpty()||rx==null||gatt==null)return;
  byte[]b=queue.remove();rx.setWriteType(BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT);rx.setValue(b);busy=true;
  if(!gatt.writeCharacteristic(rx)){busy=false;queue.clear();listener.error("Запись BLE не начата");}
 }
 public void close(){closed=true;usable=false;stopScan();unregisterBond();queue.clear();main.removeCallbacksAndMessages(null);if(gatt!=null){gatt.disconnect();gatt.close();gatt=null;}}
}
