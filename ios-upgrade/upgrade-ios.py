from netmiko import ConnectHandler
import getpass
import sys
import time

tftp_server = input('Enter IP from TFTP Server: ')
date_to_reload = input('Enter the time when to reload ex.."20:00 Februar 10": ')
username = input('Enter Username: ')
pswd = getpass.getpass('Password:')

switch_image_md5 = { #Enter Model number (search with: show version | inc Model number), image file, image hash
    'WS-C3560CX-8PC-S': ('c3560cx-universalk9-mz.152-7.E.bin', 'af45f32d707678acdaedf488237ebcad'),
    'WS-C2960X-48FPS-L': ('c2960x-universalk9-mz.152-7.E0a.bin', '56754cd55e42d84acea5dfd1628d99b9'),
    'WS-2960X-24PS-L': ('c2960x-universalk9-mz.152-7.E0a.bin', '56754cd55e42d84acea5dfd1628d99b9')
}

def config_switch(iosImage): #Configure with the right image
    device.send_command('\n \n conf t \n boot system flash:/' + iosImage + '\n  \n end \n \n \n')
    reloading = device.send_command('reload at ' + date_to_reload,
                                    expect_string=r"System configuration")
    if device.send_command('\n',
                           expect_string=r"System configuration has been modified."):
        device.send_command('\n yes \n \n ')
    if device.send_command('\n', expect_string=r"Proceed with reload"):
        device.send_command('\n \n')
    if 'Reload scheduled for' or 'Proceed with reload?' in reloading:
        device.send_command('\n \n')

def check_image(): #System image file is "flash:/imagex.bin"
    check_image = device.send_command('show version | include image')
    return check_image

def check_model(): #Model number: WS-C3560CX-8PC-S
    check_model = device.send_command('show version | include Model number')
    return check_model

def download_ios(ios_image, ios_md5): #downloading from TFTP server and verify hash
    print('connecting with tftp server, downloading IOS Image, please wait.')
    device.send_command('copy tftp://' + tftp_server + '/' + ios_image + ' flash:/',
                        expect_string='Destination filename')
    if device.send_command('\n', expect_string=r"!") or device.send_command('\n',
                                                                            expect_string=r".") or device.send_command(
            '\n', expect_string=r"O"):
        print('running after 10min')
    print('sleeping 10')
    time.sleep(800) #Script is paused, while downloading IOS from tftp Server
    verify_hash = device.send_command('verify /md5 flash:/' + ios_image, delay_factor=10)
    if ios_md5 in verify_hash:
        config_switch(ios_image)
        print(switch + ' successful Image copied, md5 verified and planned to reload at ' + date_to_reload)
    else:
        print('MD5 hash is not the same, inspect the code or Switch')
        sys.exit(1)

def upgrade_switch():
    switch_model = check_model()
    switch_image = check_image()
    switch_type = list(switch_image_md5)
    for i in switch_type:
        if i in switch_model:
            model = i #find the model from switch_image_md5
            break
    try:
        image = (switch_image_md5.get(model)[0]) #find image (*.bin) from switch_image_md5
        hash = (switch_image_md5.get(model)[1]) #find hash from switch_image_md5
    except:
        print('Switch model not found, please add it to switch_image_md5')
        sys.exit(1)
    if model in switch_model:
        if image in switch_image:
            print('*' * 100)
            print(switch + ' has the Image as provided above')
        else:
            global date_to_reload
            testing_date = validate_date(date_to_reload)
            while testing_date != True:
                date_to_reload = input('Enter the time to reload ex.."20:00 Februar 10": ')
                testing_date = validate_date(date_to_reload)
            if not check_image_dir(image):
                download_ios(image, hash)
            else:
                print(switch + ' Image found in Flash:/' + image)
                config_switch(image)
                print(switch + '  Successful planned to reload at ' + date_to_reload)

def check_image_dir(image_dir):
    dir_image = device.send_command('dir | i ' + image_dir)
    return dir_image

def validate_date(valid_date):
    reload = device.send_command_timing('reload at ' + valid_date)
    if '% Ambiguous command' in reload:
        print('Not a date, try again ex.. "20:00 Jan 10" ')
    elif '% Incomplete command.' in reload:
        print('incomplete command, try again ex.. "20:00 Jan 10" ')
    elif '%Command ignored--the specified time is too far in the future.' in reload:
        print('Cisco allows maximum 25 Days, try again: ')
    elif 'Reload scheduled for' in reload:
        device.send_command('\n\n')
        return True
    return False

with open('switch_to_upgrade') as f:
    for switch in f:
        try:
            device = ConnectHandler(device_type='cisco_ios', ip=switch, username=username, password=pswd)
            upgrade_switch()
        except:
            print('*' * 30)
            print(switch + ' could not connect')
