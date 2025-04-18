"""
配置文件设定基础参数
"""
SIMULATION_ELAPSE = 720000
ARRIVAL_RATE = 30 / 3600 #到达率

# Warehouse
NUM_OF_AISLES = 16#30 40
NUM_OF_LOCATIONS = 30#20 30 40
NUM_OF_ROBOTS = 20#
NUM_OF_PICKERS =20 #
NUM_OF_AREAS = 2 #

WIDTH_OF_SHELVES = 1  # f
WIDTH_OF_AISLE = 3  # wc
WIDTH_BETWEEN_AS = 1  # wl

v_picker = 0.75#
v_robot = 3#
#v_conveyer = 1.5#2
NUM_OF_ORDERS = 64 #80-180

pTperItem = 5
sTperItem = 0#不考虑分拣的时间，仅考虑拣选时间
log_level = 10

Recover_Rate=0.0025
Pick_Fatigue=0.0052
Travel_Fatigue=0.004

TotalDis = (NUM_OF_LOCATIONS*WIDTH_OF_SHELVES +2*WIDTH_OF_SHELVES)*NUM_OF_AISLES + 2*(NUM_OF_AISLES-1)*WIDTH_OF_AISLE

## 三种模式动态选用，哪些模式在某些订单到达率下更适用。根据订单的变化，选用协同的模式，
## 强化学习的方法。