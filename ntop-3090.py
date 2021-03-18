import os
import time
import psutil
from tabulate import tabulate

import math

def color_str(percent, line_len=25):
    percent_per_len = 100 / line_len
    cnt = round(percent/percent_per_len)
    line_list = ['|']*cnt + [' ']*(line_len-cnt)
    percent_list = list('%.1f%%'%(percent,))
    line_list[-len(percent_list):] = percent_list
    line_str = ''.join(line_list)
    if percent <= 30:
        middle_str = "\033[32m" + line_str + "\033[0m"
    elif percent <= 70:
        middle_str = "\033[34m" + line_str + "\033[0m"
    else:
        middle_str = "\033[31m" + line_str + "\033[0m"
    return '['+middle_str+']'


if __name__ == "__main__":
    # CPU
    cpu_count = psutil.cpu_count()
    cpu_percent = psutil.cpu_percent()
    cpu_len = round(cpu_percent/5)
    cpu_str = 'CPU ' + color_str(cpu_percent, 20) + ' %.1f/%d'%(cpu_percent*cpu_count,100*cpu_count)

    # Mem
    mem = psutil.virtual_memory()
    mem_total = mem.total/(1024**3)
    mem_used = mem_total - mem.available/(1024**3)
    mem_percent = mem.percent
    mem_str = 'Mem ' + color_str(mem_percent, 20) + ' %.1fG/%.1fG'%(mem_used,mem_total)
    print('\n'+cpu_str+'\t'+mem_str)
    print(' ')

    # nvidia-smi
    raw_processes = []
    gpu_util = []
    memory_usage = []
    raw_text = os.popen('nvidia-smi').read().split('\n')
    ifprocess = False
    for line in raw_text:
        # print(line)
        if line == '|=============================================================================|':
            ifprocess = True
        if 'MiB' in line and ifprocess == False:
            memory_usage.append(' / '.join([s for s in line.split(' ') if 'MiB' in s]))
            gpu_util.append([s for s in line.split(' ') if '%' in s][1])
        elif 'MiB' in line and ifprocess == True:
            raw_processes.append(line)
    memory_usage_per = []
    for item in memory_usage:
        item = item.replace('MiB','').split(' ')
        nmem_per_float = float(item[0]) / float(item[-1])
        nmem_per_str = ' %.1f%%'%(nmem_per_float*100,)
        memory_usage_per.append(nmem_per_str)

    nv1_headers = ['GPU', '   Memory-Usage   ', 'Util', 'GPU', '   Memory-Usage   ', 'Util']
    nv1_data = []
    line_num = math.ceil(len(memory_usage)/2)
    total_num = len(memory_usage)
    for i in range(line_num):
        if total_num >=2:
            nv1_data.append((
                i, memory_usage[i]+memory_usage_per[i], gpu_util[i], 
                i+line_num, memory_usage[i+line_num]+memory_usage_per[i+line_num], gpu_util[i+line_num]
                ))
        elif total_num == 1:
            nv1_data.append((
                i, memory_usage[i]+memory_usage_per[i], gpu_util[i]
                ))
        total_num -= 2
    print(tabulate(nv1_data, headers=nv1_headers, tablefmt='simple', stralign='center', numalign='center'), '\n')

    splited_processes = []
    for line in raw_processes:
        items = [c for c in line.split(' ') if c][1:-1]
        # print(items)
        mem_tmp = int(items[6].replace('MiB',''))
        # print(type(mem_tmp), mem_tmp)
        if mem_tmp < 250:
            continue
        splited_processes.append(items)

    nv2_headers = ['GPU', 'PID', 'Gmemory', 'User', 'CMD']
    nv3_headers = ['GPU', 'PID', 'User ', 'Threads', 'CPU / %', 'Mem / GB', ' Time ', ' Time+']
    nv2_data, nv3_data = [], []
    pids = {}
    for l in splited_processes:
        pid = l[3]
        p = psutil.Process(int(pid))
        username = p.username()
        threads = p.num_threads()
        cpu_use = p.cpu_percent(interval=0.1)
        mem_use = (p.memory_percent()*mem_total)/100
        tt = p.cpu_times()
        t_plus = tt.user + tt.system
        h_plus = math.floor(t_plus/3600)
        m_plus = math.floor((t_plus-3600*h_plus)/60)
        t = time.time()-p.create_time()
        h = math.floor(t/3600)
        m = math.floor((t-3600*h)/60)
        # print(p.cmdline())
        cmdline_tmp = p.cmdline()
        cmdline = ' '.join([cmdline_tmp[0].split('/')[-1]] + cmdline_tmp[1:])
        nv2_data.append(
            (l[0], l[3], l[6], username, cmdline[:50])
        )
        if pid not in pids.keys():
            time_rel = '%dh %dm'%(h,m)
            time_cpu = '%dh %dm'%(h_plus,m_plus)
            pids[pid] = {'gpus': [], 'info': [pid, username, threads, cpu_use, mem_use, time_rel, time_cpu]}
            # nv3_data.append((pid, username, threads, cpu_use, mem_use, time_rel, time_cpu))
        pids[pid]['gpus'].append(l[0])
        nv3_data = []
        for pid, info in pids.items():
            nv3_data.append(tuple([','.join(pids[pid]['gpus'])] + pids[pid]['info']))
    print(tabulate(nv2_data, headers=nv2_headers, tablefmt='simple', stralign='left', numalign='center'), '\n')
    # print(' ')
    print(tabulate(nv3_data, headers=nv3_headers, tablefmt='simple', stralign='center', numalign='center'), '\n')
    # print(' ')
    print(' PID Ignored: GPU Memory-Usage < 250 MiB \n')

