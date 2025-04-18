import simpy
import logging
import numpy as np
import random
import simpy
import numpy as np
from typing import List, Tuple
from MachineSetting import MachineList
from PickerSettingUnbind import PickerList
from Config import *
class MultiPicking(simpy.Environment):
    def __init__(self):
        super().__init__()
        self.robots = MachineList(self, num_of_robots = NUM_OF_ROBOTS)
        self.pickers = PickerList(self, num_of_pickers = NUM_OF_PICKERS)
        self.order_idx = 1
        self.served = 0
        self.process(self.orderArrive())
        self.robot_queue_record = [0, 0] # record[0]: throughput times, record[1]: sum of all queues
        self.waiting_time: List[float] = []  # 1/(mu-lambda)
        self.serve_time: List[float] = []
        self.total_time: List[float] = []
        self.walking_distance: List[float] = []

    def orderArrive(self):
        while True:
            time_interval = random.expovariate(ARRIVAL_RATE)
            yield self.timeout(time_interval)
            #logging.log(10, f"{self.now:.2f}, Batch-{self.order_idx} arrived")
            self.process(self.serve(self.order_idx))
            self.order_idx += 1

    def serve(self, client_id):
        arrive_time = self.now
        random.seed(client_id)
        orderlist: list = [0] * NUM_OF_ORDERS
        for i in range(NUM_OF_ORDERS):
            orderlist[i] = [random.randint(1, NUM_OF_AISLES), random.randint(1, NUM_OF_LOCATIONS)]
        orderlist.sort(key=lambda x: (x[0], x[1]))
        for i in range(NUM_OF_ORDERS):
            originalaisle = orderlist[i][0]
            originallocation = orderlist[i][1]
            if (originalaisle % 2 == 0):
                orderlist[i] = [originalaisle, NUM_OF_LOCATIONS + 1 - originallocation]
        target_machine = yield self.robots.get_robot(orderlist[0])
        getMachineTime = self.now
        waiting_time = getMachineTime - arrive_time
        serve_time = 0
        picker, start_spot, end_spot = self.pickers.get_firstpicker([orderlist[0], orderlist[NUM_OF_ORDERS - 1]])
        target_picker = yield picker
        getPickerTime = self.now
        waiting_time += getPickerTime - getMachineTime
        distance1 = target_picker.picker_travel_distance(start_spot)
        distance2 = target_picker.picker_travel_distance(end_spot)
        if (distance2<distance1):
            k = start_spot
            start_spot = end_spot
            end_spot = k
        if start_spot != orderlist[0]:
            orderlist.reverse()
        robot_TravelTime_1stspot = target_machine.robot_travel_distance(start_spot) / v_robot
        picker_TravelTime_1stspot = target_picker.picker_travel_distance(start_spot) / v_picker
        TravelTime_1stspot = max(robot_TravelTime_1stspot, picker_TravelTime_1stspot + pTperItem)
        #ging.log(10,
        #            f"批次订单由近端开始：{self.now},车-{target_machine.index}行走{robot_TravelTime_1stspot:.2f}s, 人-{target_picker.index}行走{picker_TravelTime_1stspot:.2f}s, serve_time:{TravelTime_1stspot:.2f}")
        # 一次拣选，更新人的位置与行走距离
        yield self.timeout(TravelTime_1stspot)
        getMachineTime = self.now
        target_picker.aisle = start_spot[0]
        target_picker.location = start_spot[1]
        target_machine.aisle = start_spot[0]
        target_machine.location = start_spot[1]
        target_picker.traveled_dis += target_picker.picker_travel_distance(start_spot)
        self.walking_distance.append(picker_TravelTime_1stspot * v_picker)
        self.pickers.put(target_picker)
        serve_time += TravelTime_1stspot
        for i in range(2,NUM_OF_ORDERS):
            spot = orderlist[i]
            target_picker = yield self.pickers.get_picker(spot)
            getPickerTime = self.now
            waiting_time += getPickerTime - getMachineTime
            robot_TravelTime_1stspot = target_machine.robot_travel_distance(spot) / v_robot
            picker_TravelTime_1stspot = target_picker.picker_travel_distance(spot) / v_picker
            TravelTime_1stspot = max(robot_TravelTime_1stspot, picker_TravelTime_1stspot + pTperItem)
            #logging.log(10, f"当前时间：{self.now},车-{target_machine.index}行走{robot_TravelTime_1stspot:.2f}s, 人-{target_picker.index}行走{picker_TravelTime_1stspot:.2f}s, serve_time:{TravelTime_1stspot:.2f}")
            #一次拣选，更新人的位置与行走距离
            yield self.timeout(TravelTime_1stspot)
            getMachineTime = self.now
            target_picker.aisle = spot[0]
            target_picker.location = spot[1]
            target_machine.aisle = spot[0]
            target_machine.location = spot[1]
            target_picker.traveled_dis += target_picker.picker_travel_distance(spot)
            self.walking_distance.append(picker_TravelTime_1stspot * v_picker)
            self.pickers.put(target_picker)
            serve_time += TravelTime_1stspot
        robot_BacktoDepot = get_distance(orderlist[NUM_OF_ORDERS-1], [1/2*NUM_OF_AISLES, 0]) / v_robot
        yield self.timeout(robot_BacktoDepot)
        self.robots.put(target_machine)
        yield self.timeout(sTperItem * NUM_OF_ORDERS)
        self.waiting_time.append(waiting_time)
        self.total_time.append(self.now - arrive_time)
        serve_time += robot_BacktoDepot + sTperItem * NUM_OF_ORDERS
        self.serve_time.append(serve_time)
        #logging.log(10, f"{self.now:.2f}, Batch-{client_id} has left, serve_time:{serve_time:.2f}, waiting time:{waiting_time:.2f}.")
        self.served = client_id
        self.robot_queue_record[0] += 1
        self.robot_queue_record[1] += len(self.robots.get_queue)

    def output(self):
        meanQuelength = self.robot_queue_record[1] / self.robot_queue_record[0]
        meanWalkingDis = sum(self.walking_distance) / self.served
        meanWaitingTime = sum(self.waiting_time) / len(self.waiting_time)
        meanServiceTime = sum(self.serve_time) / len(self.serve_time)
        meanWaitingTime2 = sum(self.waiting_time) / self.served
        meanServiceTime2 = sum(self.serve_time) / self.served
        meanTotalTime = sum(self.total_time) / len(self.total_time)
        logging.log(50, "RPOnetoKunbind\n"
                        f"{'-' * 30}\nTotal Simulation time: {SIMULATION_ELAPSE} s\n"
                        f"Arrive: {self.order_idx}\n"
                        f"Served: {self.served}\n"
                        f"Mean Queue Length:{self.robot_queue_record[1] / self.robot_queue_record[0]:.2f}\n"
                        f"Mean Walking Distance:{sum(self.walking_distance) / self.served:.2f} m\n"
                        f"Mean Waiting Time:{sum(self.waiting_time) / len(self.waiting_time):.2f} s\n"
                        f"Mean Service Time:{sum(self.serve_time) / len(self.serve_time):.2f} s\n"
                        f"Mean Total Time:{sum(self.total_time) / len(self.total_time):.2f} s"
                        )
        mylist = list((self.order_idx,self.served,meanQuelength,meanWalkingDis,meanWaitingTime,meanServiceTime,meanTotalTime))
        return mylist


def get_distance(spot1, spot2):
        now_aisle = spot1[0]
        now_location = spot1[1]
        next_aisle = spot2[0]
        next_location = spot2[1]
        if (next_aisle == now_aisle):
            return abs(now_location - next_location) * WIDTH_OF_SHELVES
        else:
            if (NUM_OF_LOCATIONS > now_location + next_location):
                return abs(now_aisle - next_aisle) * WIDTH_OF_AISLE + (now_location + next_location) * WIDTH_OF_SHELVES
            else:
                return abs(now_aisle - next_aisle) * WIDTH_OF_AISLE + (
                        2 * NUM_OF_LOCATIONS - (now_location + next_location)) * WIDTH_OF_SHELVES