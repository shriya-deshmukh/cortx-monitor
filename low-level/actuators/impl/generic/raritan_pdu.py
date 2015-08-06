"""
 ****************************************************************************
 Filename:          raritan_pdu.py
 Description:       Handles messages to the Raritan PDU
 Creation Date:     06/24/2015
 Author:            Jake Abernathy

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import json
import time
import serial

from zope.interface import implements
from actuators.Ipdu import IPDU

from framework.base.debug import Debug
from framework.utils.service_logging import logger

class RaritanPDU(Debug):
    """Handles request messages to the Raritan PDU"""

    implements(IPDU)

    ACTUATOR_NAME = "RaritanPDU"

    # Section and keys in configuration file
    RARITANPDU      = ACTUATOR_NAME.upper()
    USER            = 'user'
    PASS            = 'pass'
    COMM_PORT       = 'comm_port'
    MAX_LOGIN_TRIES = 'max_login_attempts'

    MAX_CHARS       = 32767

    @staticmethod
    def name():
        """ @return: name of the module."""
        return RaritanPDU.ACTUATOR_NAME

    def __init__(self, conf_reader):
        super(RaritanPDU, self).__init__()

        # Read in the configuration values
        self._conf_reader = conf_reader
        self._read_config()

    def perform_request(self, jsonMsg):
        """Performs the PDU request

        @return: The response string from the PDU
        """
        self._check_debug(jsonMsg)

        response = "N/A"
        try:
            # Parse out the login request to perform
            node_request = jsonMsg.get("actuator_request_type").get("node_controller").get("node_request")
            self._log_debug("perform_request, node_request: %s" % node_request)

            # Parse out the command to send to the PDU
            pdu_request = node_request[5:]
            self._log_debug("perform_request, pdu_request: %s" % pdu_request)

            # Create the serial port object and open the connection
            self._connection = serial.Serial(self._comm_port, 115200 , timeout=1)

            # Send user/pass until max attempts has been reached
            login_attempts = 0
            while login_attempts < self._max_login_attempts:
                try:
                    if self._login_PDU() == True:
                        break
                except RuntimeError as re:
                    self._log_debug("RuntimeError attempting to login to PDU: %s" % re)
                login_attempts += 1

            # Error out of we exceeded max attempts
            if login_attempts == self._max_login_attempts:
                raise Exception("Warning: Maximum login attempts exceeded \
                                to Raritan PDU without success")

            self._log_debug("perform_request, Successfully logged into PDU")

            # Send the request and read the response
            response = self._send_request_read_response(pdu_request)

            # Apply some validation to the response and retry as a safety net
            if self._validate_response(response) == False:
                response = self._send_request_read_response(pdu_request)

        except Exception as e:
            logger.exception(e)
            response = str(e)

        finally:
            self._logout_PDU()

        return response

    def _send_request_read_response(self, pdu_request):
        """Sends the request and returns the string response"""
        self._connection.write(pdu_request + "\n")
        return self._connection.read(self.MAX_CHARS)

    def _login_PDU(self):
        """Sends the username and password to logon

        @return True if login was successful
        @raise RuntimeError: if an error occurs"""

        # Send the username and read the response
        response = self._send_request_read_response(self._user)
        self._log_debug("_login_PDU, wrote username: %s" % self._user)

        # Send over the password if it is requested
        if "Password:" in response:
             self._log_debug("_login_PDU, Password requested, sending")
             # Send the password
             response = self._send_request_read_response(self._pass)
             # A successful login prompt is denoted by the '#'
             if "#" in response:
                 return True
             else:
                 raise RuntimeError("ERROR: authentication failure")

        # A successful login prompt is denoted by the '#' from previous session
        elif "#" in response:
            return True

        # Login attempt failed
        else:
            raise RuntimeError("ERROR: no password prompt returned from PDU")

    def _logout_PDU(self):
        """Sends an exit command to properly logout and close connection"""       
        try:
            # Attempt to properly exit the session
            self._connection.write("exit\n")
        except:
            pass
        # Close the connection
        self._connection.close()

    def _validate_response(self, response):
        """Checks the response for the 'Available commands:' in response

        If the PDU returns a list of available commands then it did
            not recognize our command in which case we need to back
            out and try again as a safety net.

        @return: False if 'Available commands:' found in response otherwise True
        """
        if "Available commands:" in response:
            self._log_debug("Response shows list of available commands")
            # Reset the prompt by backspacing a large amount to put back on prompt
            for x in range(0, 500):
                self._connection.write("\b")
            return False
        return True

    def _read_config(self):
        """Read in configuration values"""
        try:
            self._user = self._conf_reader._get_value_with_default(self.RARITANPDU,
                                                                   self.USER,
                                                                   'admin')
            self._pass = self._conf_reader._get_value_with_default(self.RARITANPDU,
                                                                   self.PASS,
                                                                   'admin')
            self._comm_port = self._conf_reader._get_value_with_default(self.RARITANPDU,
                                                                   self.COMM_PORT,
                                                                   '/dev/ttyACM0')
            self._max_login_attempts = int(self._conf_reader._get_value_with_default(self.RARITANPDU,
                                                                   self.MAX_LOGIN_TRIES,
                                                                   5))

            logger.info("PDU Config: user: %s, Comm Port: %s, max login attempts: %s" % 
                            (self._user, self._comm_port, self._max_login_attempts))
        except Exception as e:
            logger.exception(e)