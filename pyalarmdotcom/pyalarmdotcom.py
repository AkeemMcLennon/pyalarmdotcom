from __future__ import with_statement

"""
Requires phantomjs 2.0
"""

from selenium import webdriver
from selenium.common import exceptions
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import logging
import urllib.error

_LOGGER = logging.getLogger(__name__)

class LoginException(Exception):
    """ 
    Raise when we are unable to log into alarm.com
    """
    pass


class SystemArmedError(Exception):
    """
    Raise when the system is already armed and an attempt
    to arm it again is made.
    """
    pass


class SystemDisarmedError(Exception):
    """
    Raise when the system is already disamred and an attempt
    to disarm the system is made.
    """
    pass


class ElementException(Exception):
    """
    Raise when we are unable to locate an element on the page.
    """
    pass


class Alarmdotcom(object):
    """
    Access to alarm.com partners and accounts.

    This class is used to interface with the options available through
    alarm.com. The basic functions of checking system status and arming
    and disarming the system are possible.
    """

    # Page elements on alarm.com that are needed
    # Using a dict for the attributes to set whether it is a name or id for locating the field
    LOGIN_URL = 'https://www.alarm.com/login?m=no_session&ReturnUrl=/web/Security/SystemSummary.aspx'
    LOGIN_USERNAME = ('name', 'ctl00$ContentPlaceHolder1$loginform$txtUserName')
    LOGIN_PASSWORD = ('name', 'txtPassword')
    LOGIN_BUTTON = ('name', 'ctl00$ContentPlaceHolder1$loginform$signInButton')

    STATUS_IMG = ('id', 'ctl00_phBody_ArmingStateWidget_imgState')
    
    BTN_DISARM = ('id', 'ctl00_phBody_ArmingStateWidget_btnDisarm')
    BTN_ARM_STAY = ('id', 'ctl00_phBody_ArmingStateWidget_btnArmStay', 'ctl00_phBody_ArmingStateWidget_btnArmOptionStay')
    BTN_ARM_AWAY = ('id', 'ctl00_phBody_ArmingStateWidget_btnArmAway', 'ctl00_phBody_ArmingStateWidget_btnArmOptionAway')

    # Image to check if hidden or not while the system performs it's action.
    STATUS_UPDATING = {'id': 'ctl00_phBody_ArmingStateWidget_imgArmingUpdating'}
    
    def __init__(self, username, password, timeout=5):
        """
        Open a selenium connection.
 
        This uses the PhantomJS library with selenium. We will attempt to keep the
        connection alive but if we need to reconnect we will.
        """
        self.username = username
        self.password = password
        self.timeout = timeout
        if not self._login():
            raise LoginException('Unable to login to alarm.com')


    def _login(self):
        """
        Login to alarm.com
        """
        # Attempt to login to alarm.com
        self._driver = webdriver.PhantomJS()
        self._driver.get(self.LOGIN_URL)
  
        # Check the login title to make sure it is the right one.
        if self._driver.title == 'Customer Login':
            user = self._driver.find_element(by=self.LOGIN_USERNAME[0], value=self.LOGIN_USERNAME[1])
            pwd = self._driver.find_element(by=self.LOGIN_PASSWORD[0], value=self.LOGIN_PASSWORD[1])
            btn = self._driver.find_element(by=self.LOGIN_BUTTON[0], value=self.LOGIN_BUTTON[1])

            _LOGGER.debug('Sending login credentials to alarm.com')
            user.send_keys(self.username)
            pwd.send_keys(self.password)
            btn.click() 
           
            if self._driver.title == 'Current System Status':
                _LOGGER.info('Successful login to alarm.com')
                return True
            else:
                _LOGGER.error('Unable to login to alarm.com')
                return False
        else:
            _LOGGER.error('Unable to locate alarm.com Customer login page.')
            return False

    def _set_state(self, btn, timeout=10):
        """
        Wait for the status to complete it's update.
        """

        _LOGGER.debug('Attemting to change state of alarm.')
        button = WebDriverWait(self._driver, self.timeout).until(EC.visibility_of_element_located((btn[0], btn[1])))
        button.click()

        # If the particular command needs to have a second option clicked.
        if len(btn) > 2:
            _LOGGER.debug('Secondary option is available with this command. Attempt to locate and click.')
            opt_button = WebDriverWait(self._driver, self.timeout).until(EC.visibility_of_element_located((btn[0], btn[2])))
            opt_button.click()
            # Loop until the system updates the status
            try:
                _LOGGER.info('Waiting for system to change status.')
                WebDriverWait(self._driver,
                              timeout).until(EC.invisibility_of_element_located(('id','ctl00_phBody_ArmingStateWidget_imgPopupSpinner')))
            except exceptions.TimeoutException:
                raise ElementException('Timeout while trying to locate the secondary option.')

    @property
    def state(self):
        """
        Check the current status of the alarm system.
        """
        # Click the refresh button to verify the state if it was made somewhere else
        try:
            button = WebDriverWait(self._driver, self.timeout).until(EC.visibility_of_element_located(('id', 'ctl00_phBody_ArmingStateWidget_btnArmingRefresh')))
            button.click()
            # Recheck the current status
            current_status = WebDriverWait(self._driver, self.timeout).until(EC.presence_of_element_located((self.STATUS_IMG[0],
                                                   self.STATUS_IMG[1]))).get_attribute('alt')
            _LOGGER.debug('Fetched current status from system: {}'.format(current_status))
            return current_status
        except (exceptions.NoSuchElementException, exceptions.NoSuchWindowException, exceptions.TimeoutException, urllib.error.URLError) as e:
            _LOGGER.warning('Error while checking alarm status. Attempting login again.')
            self._login()
            return self.state

    def disarm(self):
        """
        Disarm the alarm system
        """
        if self.state != 'Disarmed':
            _LOGGER.info('Disarming system.')
            self._set_state(self.BTN_DISARM)
        else:
            raise SystemDisarmedError('The system is already disarmed!')

    def arm_away(self):
        """
        Arm the system in away mode.
        """
        if self.state == 'Disarmed':
            _LOGGER.info('Arming system in away mode.')
            self._set_state(self.BTN_ARM_AWAY)
        else:
            raise SystemArmedError('The system is already armed!')

    def arm_stay(self):
        """
        Arm the system in stay mode.
        """
        if self.state == 'Disarmed':
            _LOGGER.info('Arming system in stay mode.s')
            self._set_state(self.BTN_ARM_STAY)
        else:
            raise SystemArmedError('The system is already armed!')
