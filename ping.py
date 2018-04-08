import argparse
import csv
import socket
import os, shutil
from multiprocessing import Process, Manager, Value, Lock
from subprocess import Popen, PIPE, TimeoutExpired
from ipaddress import ip_network
from datetime import datetime


class Counter(object):
    def __init__(self, initval=0):
        self.val = Value('i', initval)
        self.lock = Lock()

    def increment(self):
        with self.lock:
            self.val.value += 1

    def value(self):
        with self.lock:
            return self.val.value


def generate_args():
    """ Create main parser """
    parser = argparse.ArgumentParser(prog='ping.py')
    # Create global arguments
    parser.add_argument('--hosts', dest='hosts', type =str, help="Specify network to ping using CIDR notation."
                                                                 "Example: 10.0.0.0/24",
                        required=True)
    args = parser.parse_args()
    return args

def subnet_ping(ip, counter, ip_results):
    """ Run ping subprocess and keep track of ping result
        Append results to a list of dictionaries """
    # Linux/mac
    if os.name == 'posix':
        sub_p = Popen(['ping', '-c', '4', str(ip)], stdout=PIPE, stderr=PIPE, stdin=PIPE)
    # Windows
    elif os.name == 'nt':
        sub_p = Popen(['ping', '-n', '4', str(ip)], stdout=PIPE, stderr=PIPE, stdin=PIPE)
    # grab output and errors from subprocess
    try:
        output, errors = sub_p.communicate(timeout=15)
    except TimeoutExpired:
        sub_p.kill()
        output, errors = sub_p.communicate()
    # differences in output of poxis vs nt
    if os.name == 'posix':
        # if you don't see 0 packets in the output, then you must have received packets from the host
        if not '0 packets received' in str(output):
            #print(ip, 'is up!', "\n")
            log_out = "{} is up! \n".format(ip)
            log_file(log_out)
            counter.increment()
            ip_results.append({'ip': ip, 'status': 'up'})
        else:
            #print(ip, "is down or can't be pinged!", "\n")
            log_out = "{} is down or can't be pinged! \n".format(ip)
            log_file(log_out)
            ip_results.append({'ip': ip, 'status': 'down'})
    elif os.name == 'nt':
        if not 'Received = 0' in str(output):
            #print(ip, 'is up!', "\n")
            log_out = "{} is up! \n".format(ip)
            log_file(log_out)
            counter.increment()
            ip_results.append({'ip': ip, 'status': 'up'})
        else:
            #print(ip, "is down or can't be pinged!", "\n")
            log_out = "{} is down or can't be pinged! \n".format(ip)
            log_file(log_out)
            ip_results.append({'ip': ip, 'status': 'down'})

def log_file(info):
    """ Write to a log file """
    ## FIX - Windows seems to have a problem using the global reference log_filename ##
    with open('ping_log.txt', 'a+') as f:
        f.write(str(info))

def export_hosts_to_csv(hosts):
    with open('ping_results.csv', 'w+', newline='') as csvfile:
        fieldnames = ['ip', 'status']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for host in hosts:
            writer.writerow({'ip': host['ip'], 'status': host['status']})



if __name__ == '__main__':
    args = generate_args()
    # use manager for sharing the list between processes
    manager = Manager()
    ip_results = manager.list()
    # if mac set number of open files from default 256 to 10240 for this parent process and all subs
    if os.name == 'posix':
        import resource
        resource.setrlimit(resource.RLIMIT_NOFILE, (10240, 10240))
    hosts = args.hosts
    # shared counter for all processes to have access to increment
    counter = Counter(0)
    dt = datetime.now()
    log_filename = "ping_log.txt"
    archive_log_filename = "ping_log_{}_{}_{}_{}_{}_{}.txt".format(dt.month, dt.day, dt.year, dt.hour,
                                                                   dt.minute, dt.second,)
    archive_logfile_path = "Archive/{}".format(archive_log_filename)
    # remove old log file if it exists, create new archive folder if one doesn't exist, move old to archive
    if not os.path.exists('Archive'):
        os.mkdir('Archive')
    if os.path.exists(log_filename):
        os.rename(log_filename, archive_log_filename)
        shutil.move(archive_log_filename, archive_logfile_path)

    # build ips
    hosts = list(ip_network(hosts).hosts())
    hosts = [str(host) for host in hosts]
    # grab total number of hosts within the subnet to ping (length of list)
    total_hosts = len(hosts)
    # create process queue for each ip to be pinged. Prob need to look into better management of this
    processes = []
    workers = [0 for x in range(50)]
    # increment on index of ip_addr because a list is returned
    idx = 0
    # grab number of IPs - later count down to 0
    hosts_len = len(hosts)
    try:
        while hosts_len > 0:
            if 0 not in workers:
                workers = [0 for x in range(50)]
            for w in range(len(workers)):
                p = Process(target=subnet_ping, args=(hosts[idx], counter, ip_results))
                # start the process
                p.start()
                # add to list of workers available to run processes
                processes.append(p)
                workers.remove(0)
                idx += 1
                hosts_len -= 1
            # calling process blocked until process who's join method is called terminates.
            # used more or less for queuing. If join is not used all processes join immediately
            # you can also specify an optional timeout in case waiting is too long
            for p in processes:
                p.join()
    except IndexError:
        pass

    # continually check if process is still alive, when done provide results
    process_running = True
    while process_running:
        if not processes[-1].is_alive():
            print("{} of {} hosts could be pinged.".format(counter.value(), total_hosts))
            host_result_summary = "\n{} of {} hosts could be pinged.".format(counter.value(), total_hosts)
            datetime_completed = "\nCompleted on {}/{}/{} @ {}:{}:{}".format(dt.month,dt.day, dt.year,dt.hour,
                                                                         dt.minute, dt.second)
            log_file(host_result_summary)
            log_file(datetime_completed)
            # sort the results from first ip to last by using socket's builtin inet_aton
            ip_results = sorted(ip_results, key=lambda host: socket.inet_aton(host['ip']))
            export_hosts_to_csv(ip_results)
            process_running = False
        else:
            continue



















