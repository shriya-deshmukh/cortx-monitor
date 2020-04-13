# -*- coding: utf-8 -*-
import json
import os
import psutil
import time
import sys

from sspl_test.default import *
from sspl_test.rabbitmq.rabbitmq_ingress_processor_tests import RabbitMQingressProcessorTests
from sspl_test.rabbitmq.rabbitmq_egress_processor import RabbitMQegressProcessor

def init(args):
    pass

def test_real_stor_fan_module_actuator(agrs):
    check_sspl_ll_is_running()
    fan_actuator_message_request("ENCL:enclosure:fru:fan", "4")
    fan_module_actuator_msg = None
    time.sleep(4)
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        ingressMsg = world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()
        time.sleep(2)
        print("Received: %s" % ingressMsg)
        try:
            # Make sure we get back the message type that matches the request
            msg_type = ingressMsg.get("actuator_response_type")
            if msg_type["info"]["resource_type"] == "enclosure:fru:fan":
                fan_module_actuator_msg = msg_type
                break
        except Exception as exception:
            time.sleep(4)
            print(exception)

    assert(fan_module_actuator_msg is not None)
    assert(fan_module_actuator_msg.get("alert_type") is not None)
    assert(fan_module_actuator_msg.get("alert_id") is not None)
    assert(fan_module_actuator_msg.get("severity") is not None)
    assert(fan_module_actuator_msg.get("host_id") is not None)
    assert(fan_module_actuator_msg.get("info") is not None)

    fan_module_info = fan_module_actuator_msg.get("info")
    assert(fan_module_info.get("site_id") is not None)
    assert(fan_module_info.get("node_id") is not None)
    assert(fan_module_info.get("cluster_id") is not None)
    assert(fan_module_info.get("rack_id") is not None)
    assert(fan_module_info.get("resource_type") is not None)
    assert(fan_module_info.get("event_time") is not None)
    assert(fan_module_info.get("resource_id") is not None)

    fru_specific_info = fan_module_actuator_msg.get("specific_info", {})

    resource_id = fan_module_info.get("resource_id")
    if resource_id == "*":
        verify_fan_module_specific_info(fru_specific_info)
        return

    if fru_specific_info:
        assert(fru_specific_info.get("durable_id") is not None)
        assert(fru_specific_info.get("status") is not None)
        assert(fru_specific_info.get("name") is not None)
        assert(fru_specific_info.get("enclosure_id") is not None)
        assert(fru_specific_info.get("health") is not None)
        assert(fru_specific_info.get("health_reason") is not None)
        assert(fru_specific_info.get("location") is not None)
        assert(fru_specific_info.get("health_recommendation") is not None)
        assert(fru_specific_info.get("position") is not None)

    fans = fan_module_actuator_msg.get("specific_info").get("fans", [])
    if fans:
        for fan in fans:
            assert(fan.get("durable_id") is not None)
            assert(fan.get("status") is not None)
            assert(fan.get("name") is not None)
            assert(fan.get("speed") is not None)
            assert(fan.get("locator_led") is not None)
            assert(fan.get("position") is not None)
            assert(fan.get("location") is not None)
            assert(fan.get("part_number") is not None)
            assert(fan.get("serial_number") is not None)
            assert(fan.get("fw_revision") is not None)
            assert(fan.get("hw_revision") is not None)
            assert(fan.get("health") is not None)
            assert(fan.get("health_reason") is not None)
            assert(fan.get("health_recommendation") is not None)

def verify_fan_module_specific_info(fru_specific_info):
    """Verify fan_module specific info"""

    if fru_specific_info:
        for fru_info in fru_specific_info:
            assert(fru_info.get("durable_id") is not None)
            assert(fru_info.get("status") is not None)
            assert(fru_info.get("name") is not None)
            assert(fru_info.get("enclosure_id") is not None)
            assert(fru_info.get("health") is not None)
            assert(fru_info.get("health_reason") is not None)
            assert(fru_info.get("location") is not None)
            assert(fru_info.get("health_recommendation") is not None)
            assert(fru_info.get("position") is not None)

            fans = fru_info.get("fans", [])
            if fans:
                for fan in fans:
                    assert(fan.get("durable_id") is not None)
                    assert(fan.get("status") is not None)
                    assert(fan.get("name") is not None)
                    assert(fan.get("speed") is not None)
                    assert(fan.get("locator_led") is not None)
                    assert(fan.get("position") is not None)
                    assert(fan.get("location") is not None)
                    assert(fan.get("part_number") is not None)
                    assert(fan.get("serial_number") is not None)
                    assert(fan.get("fw_revision") is not None)
                    assert(fan.get("hw_revision") is not None)
                    assert(fan.get("health") is not None)
                    assert(fan.get("health_reason") is not None)
                    assert(fan.get("health_recommendation") is not None)

def check_sspl_ll_is_running():
    # Check that the state for sspl service is active
    found = False

    # Support for python-psutil < 2.1.3
    for proc in psutil.process_iter():
        if proc.name == "sspl_ll_d" and \
           proc.status in (psutil.STATUS_RUNNING, psutil.STATUS_SLEEPING):
               found = True

    # Support for python-psutil 2.1.3+
    if found == False:
        for proc in psutil.process_iter():
            pinfo = proc.as_dict(attrs=['cmdline', 'status'])
            if "sspl_ll_d" in str(pinfo['cmdline']) and \
                pinfo['status'] in (psutil.STATUS_RUNNING, psutil.STATUS_SLEEPING):
                    found = True

    assert found == True

    # Clear the message queue buffer out
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()

def fan_actuator_message_request(resource_type, resource_id):
    egressMsg = {
        "title": "SSPL Actuator Request",
        "description": "Seagate Storage Platform Library - Actuator Request",

        "username" : "JohnDoe",
        "signature" : "None",
        "time" : "2015-05-29 14:28:30.974749",
        "expires" : 500,

        "message" : {
            "sspl_ll_msg_header": {
                "schema_version": "1.0.0",
                "sspl_version": "1.0.0",
                "msg_version": "1.0.0"
            },
             "sspl_ll_debug": {
                "debug_component" : "sensor",
                "debug_enabled" : True
            },
            "request_path": {
                "site_id": 1,
                "rack_id": 1,
                "cluster_id": '1',
                "node_id": 1
            },
            "response_dest": {},
            "actuator_request_type": {
                "storage_enclosure": {
                    "enclosure_request": resource_type,
                    "resource": resource_id
                }
            }
        }
    }
    world.sspl_modules[RabbitMQegressProcessor.name()]._write_internal_msgQ(RabbitMQegressProcessor.name(), egressMsg)

test_list = [test_real_stor_fan_module_actuator]
