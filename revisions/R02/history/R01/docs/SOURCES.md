# Первичные источники, просмотрены 30.09.2026

1. Kanthal, Nikrothal 80: NiCr как материал резистивного нагрева; удельное сопротивление 1,09 Ω·мм²/м при 20 °C. Эта характеристика использована в оценке проволоки, не подтверждает пригодность самодельного текстильного нагревателя.
   https://www.kanthal.com/en/products/datasheets/material-datasheets/wire/resistance-heating-wire-and-resistance-wire/nikrothal-80/
2. IEC 60335-2-17:2022, описание области применения: гибкие нагревательные приборы, в том числе питаемые DC/батареями, и их контроллеры. Полный нормативный текст и сертификационная оценка не выполнялись; не заявляется, что приведённой базовой редакцией исчерпываются актуальные требования.
   https://webstore.iec.ch/en/publication/70369
3. Espressif, USB Serial/JTAG ESP32-S3: native CDC, GPIO19 D− / GPIO20 D+.
   https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-guides/usb-serial-jtag-console.html
4. Espressif Arduino: ADC и LEDC. Конкретная аппаратная сборка здесь не выполнена.
   https://docs.espressif.com/projects/arduino-esp32/en/latest/api/adc.html
   https://docs.espressif.com/projects/arduino-esp32/en/latest/api/ledc.html
5. Microchip, TC4426/4427/4428, datasheet DS20001422G: TC4427, DIP-8, неинвертирующий драйвер, питание 4,5–18 В. Сверить точную закупаемую позицию и распиновку.
   https://ww1.microchip.com/downloads/en/DeviceDoc/20001422G.pdf
6. STMicroelectronics, STP55NF06L, datasheet: N-channel MOSFET, TO-220, выводы G/D/S.
   https://www.st.com/resource/en/datasheet/stp55nf06l.pdf
7. Nexperia, 74HC/HCT123, Rev.13 2024: retriggerable monostable, активный высокий 1Q = вывод 13, 1CEXT =14, 1REXT/CEXT =15. Timeout для выбранных R/C и 3,3 В требуется измерить.
   https://assets.nexperia.com/documents/data-sheet/74HC_HCT123.pdf
8. Android Developers, Bluetooth permissions: отдельные runtime разрешения SCAN/CONNECT для новых Android.
   https://developer.android.com/develop/connectivity/bluetooth/bt-permissions
9. jSerialComm, документация разработчика: библиотека последовательного порта Java.
   https://fazecast.github.io/jSerialComm/
10. Victron Lithium Battery Smart, технические данные: пример зависимости допустимой температуры зарядки от паспорта конкретного производителя. Его границы не переносятся автоматически на ещё не выбранную батарею проекта.
   https://www.victronenergy.com/media/pg/Lithium_Battery_Smart/en/technical-data.html

Все остальные размеры, силы, мощности зон и сценарии являются проектными предположениями или результатами приложенных расчётов, а не характеристиками испытанного серийного продукта.
