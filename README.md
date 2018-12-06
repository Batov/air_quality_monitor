# Air quality monitor

 * Raspberry Pi
 * Adafruit CCS811 Air Quality Sensor
 * Carbon Dioxide Sensor SCD30

## Hardware
```
 RPI           SCD30
-------|     |--------| 
   3V3 |-----| VIN    |
   GND |-----| GND    |
   SDA |-----| RX/SDA |
   SCL |-----| TX/SCL |
 GPIO4 |-----| RDY    |
-------|     | PWM    |
             | SEL    |
             |--------|
 
 RPI           CCS811
-------|     |--------| 
   3V3 |-----| VIN    |
   GND |-----| GND    |
   SDA |-----| SDA    |
   SCL |-----| SCL    |
       |     | ___    |
GPIO17 |-----| INT    |
       |     | ___    | 
   GND |-----| WAK    |
-------|     | ___    |
             | RST    |
             |--------|
```

![HW setup](https://pp.userapi.com/c846523/v846523934/1421eb/8oMh4Csg5aQ.jpg)

## Raspbian requirements
* Raspbian GNU/Linux 9.6 (stretch)
* Python 3.5 + pipenv
* Decrease I2C speed:
  * `sudo nano /boot/config.txt`
  * Add `dtparam=i2c_baudrate=10000`

## Install
`pipenv install`

## Run CLI
`pipenv run air_quality_monitor/src/cli_monitor.py`

## Run WEB
* `pipenv run air_quality_monitor/src/web_monitor.py`
* Open browser on 192.168.1.33:8000, where 192.168.1.33 - local RPi IP

## Project overview
* `src/`
  * `scd30.py` - driver for SCD30
  * `ccs811.py` - driver for CCS811
  * `cli_monitor.py` - CLI air monitor
  * `web_monitor.py` - WEB air monitor
* `doc/` - sensor's datasheets
* `static/` - HTML pages got web air monitor
