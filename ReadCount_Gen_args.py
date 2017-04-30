from Queue import Queue
from threading import Thread, Lock
import os
import shutil
import subprocess
import time
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--copy_to_local",default=False,type=bool,
                    help='Set True if you want to temporarily use space in local hard drive for faster processing speed.')
parser.add_argument("--allocated_space",default=None,type=int,
                    help='An integer of space temporarily given to the program. Unit is given in another argument. If not specified when copy_to_local is true, '
                         'program will use all space available in the disc where temporary folder is located at.')
parser.add_argument("--allocated_space_unit",required=True,type=str,help='The unit of allocated_space. It has to be either MB or GB, case sensitive.')
parser.add_argument("--local_poolsize",default=0,type=int,help='The number of threads, i.e. logical cores, used for processing files that are moved to temporary folders. '
                                                      'Cannot be 0 when copy_to_local is True.')
parser.add_argument("--external_poolsize",default=1,type=int,help='The number of threads, i.e. logical cores, used for processing files directly from external hard drive. '
                                                      'Cannot be 0 when copy_to_local is False.')
parser.add_argument("--coverageBed_path",default='coverageBed',type=str,help='Full path of the coverageBed software.')
parser.add_argument("--bam_folder",nargs='+',type=str,help='Full path of folder containing original source of bam files. Can accept multiple arguments separated by space, specify category in category parameter. '
                                                 'Bam files should be directly under the folder!?!?!?!?! (not in subfolders).')
parser.add_argument("--category",nargs='+',type=str,help='Category of bam folders in the exact same order provided in bam_folder parameter. Accept multiple arguments, separated by space.')
parser.add_argument("--bed_file",required=True,type=str,help='Full path of the bed files that is going to be used.')
parser.add_argument("--temp_folder",type=str,help='Full path of temporary folder if you wish to use space in local hard drive for faster processing speed. '
                                                  'Folder will be created if not previously exists.')
parser.add_argument("--output_folder",required=True,type=str,help='Full path of folder for readcount outputs, a progress file and a target file that records task progress. '
                                                    'Folder will be created if not previously exists.')
parser.add_argument("--RNA_type",required=True,type=str,help='sno,lnc,piwi,etc..This string will be incoporated into output files.')
args = parser.parse_args()
if args.local_poolsize < 0 or args.external_poolsize < 0:
    raise ValueError("local_poolsize or external_poolsize cannot be less than 0.")
if args.local_poolsize == 0 and args.external_poolsize == 0:
    raise ValueError("local_poolsize and external_poolsize cannot be 0 at the same time.")
if args.local_poolsize == 0 and args.copy_to_local == True:
    raise ValueError("local_poolsize cannot be 0 when copy_to_local is True.")
if args.external_poolsize == 0 and args.copy_to_local == False:
    raise ValueError("external_poolsize cannot be 0 when copy_to_local is False.")
if args.copy_to_local and (args.temp_folder is None):
    raise ValueError("temporary folder path has to be provided if local space is intended to be used.")
if len(args.bam_folder) != len(args.category):
    raise ValueError("number of bam folders provided should be same as number of category provided.")
copy_to_local = args.copy_to_local

coverageBed_folder = args.coverageBed_path
bam_folder_list = args.bam_folder
category = args.category
bam_category_list = []
bed_file = args.bed_file
output_folder = args.output_folder
temp_folder = args.temp_folder

free_ext_thread = 0
free_local_thread = 0

progree_file_lock = Lock()
free_ext_thread_lock = Lock()
num_finished_lock = Lock()
free_local_thread_lock = Lock()
target_file_lock = Lock()

external_queue = Queue()
copy_queue = Queue()
local_queue = Queue()

num_finished = 0
num_total = 0

def ready_paths():
    progress_file_path = "%s/finished_bams.txt"%(output_folder)
    target_file_path = "%s/target.txt"%(output_folder)
    if copy_to_local:
        if not os.path.isdir(temp_folder):
            os.makedirs(temp_folder)
            print("Created new temporary bam folder")
    if not os.path.isdir(output_folder):
        os.makedirs(output_folder)
        print("Created new readcount output folder")
    return (progress_file_path, target_file_path)

def ready_bam_files(progress_file_path):
    global num_finished
    global num_total
    global bam_category_list
    finished_bam = []
    if os.path.exists(progress_file_path):
        progress_file = open(progress_file_path, "r")
        for line in progress_file.readlines():
            finished_bam.append(line.rstrip())
            num_finished += 1
        progress_file.close()

    for j in range(len(bam_folder_list)):
        bam_names = []
        bam_folder = bam_folder_list[j]
        bam_folder_file_names = os.listdir(bam_folder)

        for i in range(len(bam_folder_file_names)):
            if bam_folder_file_names[i].endswith(".bam"):
                num_total += 1
                if bam_folder_file_names[i] not in finished_bam:
                    bam_names.append(bam_folder_file_names[i])
        for bam_name in bam_names:
            bam_category_list.append(("%s" % (bam_name),category[j]))
            copy_queue.put("%s/%s" % (bam_folder, bam_name))

def free_space_cal(allocated_space, unit):
    if copy_to_local:
        if allocated_space:
            if unit == "GB":
                unit_rate = 10**9
            elif unit == "MB":
                unit_rate = 10**6
            else:
                raise ValueError("unit has to be either MB or GB, case sensitive")
            init_free_space = allocated_space * unit_rate
            space_difference = os.statvfs(temp_folder).f_frsize * os.statvfs(
                temp_folder).f_bavail - init_free_space
            if space_difference < 0:
                init_free_space = os.statvfs(temp_folder).f_frsize * os.statvfs(temp_folder).f_bavail
                space_difference = 0
                print "not enough space to allocate, using all space available"
            return (init_free_space, space_difference)
        elif allocated_space is None:
            init_free_space = os.statvfs(temp_folder).f_frsize * os.statvfs(temp_folder).f_bavail
            space_difference = 0
            return (init_free_space, space_difference)

def copy_file(queue,init_free_space,space_difference):
    while queue.empty() is False:
        bam_file = queue.get()
        if copy_to_local:
            curr_free_space = os.statvfs(temp_folder).f_frsize * os.statvfs(temp_folder).f_bavail - space_difference
            if curr_free_space >= os.stat(bam_file).st_size:
                bam_name_suffix = bam_file.split('/')[-1]
                shutil.copyfile(bam_file,"%s/%s"%(temp_folder,bam_name_suffix))
                local_queue.put("%s/%s"%(temp_folder,bam_name_suffix))
                queue.task_done()
            elif init_free_space < os.stat(bam_file).st_size:
                external_queue.put(bam_file)
                queue.task_done()
            else:
                if free_ext_thread > 0:
                    external_queue.put(bam_file)
                else:
                    queue.put(bam_file)
                    time.sleep(2)
                queue.task_done()
        elif copy_to_local is False:
            external_queue.put(bam_file)
            queue.task_done()

def ready_target_file(bam_output,category):
    with target_file_lock:
        progress_file = open(target_file_path, "a+")
        if os.stat(target_file_path).st_size == 0:
            progress_file.write("files\tgroup\n" )
        progress_file.write("%s\t%s\n" % (bam_output,category))
        progress_file.close()

def covBed_exe(queue):
    global free_ext_thread
    global free_local_thread
    global num_finished
    if queue == external_queue:
        free_ext_thread += 1
        #print ("%s thread for external HHD created"%(free_ext_thread))
    elif queue == local_queue:
        free_local_thread += 1
        #print ("%s thread for SSD created"%(free_local_thread))
    time.sleep(0.1)
    while True:
        bam_file = queue.get()
        bam_name_suffix = bam_file.split('/')[-1]
        bam_name_nosuffix = bam_name_suffix[:-4]
        identifier = [bam_category[1] for bam_category in bam_category_list if bam_category[0] == bam_name_suffix][0]
        if queue == external_queue:
            with free_ext_thread_lock:
                free_ext_thread -= 1
            #print "%s of %s external threads currently working"%(args.external_poolsize - free_ext_thread,args.external_poolsize)
        if queue == local_queue:
            with free_local_thread_lock:
                free_local_thread -= 1
            #print "%s of %s local threads currently working" % (
            #args.local_poolsize - free_local_thread, args.local_poolsize)
        time.sleep(0.1)
        with open("%s/%s_readcount_%s.txt"%(output_folder,args.RNA_type,bam_name_nosuffix), 'w+') as output_file:
            subprocess.check_call([coverageBed_folder,"-abam",bam_file,"-b",bed_file,], stdout=output_file)
        with progree_file_lock:
            progress_file = open(progress_file_path,"a+")
            progress_file.write("%s\n"%(bam_name_suffix))
            progress_file.close()
        with num_finished_lock:
            num_finished += 1
        if queue == local_queue:
            os.remove(bam_file)
        ready_target_file("%s/%s_readcount_%s.txt"%(output_folder,args.RNA_type,bam_name_nosuffix),identifier)
        if queue == external_queue:
            with free_ext_thread_lock:
                free_ext_thread += 1
            #print "%s of %s external threads currently working" % (
            #args.external_poolsize - free_ext_thread, args.external_poolsize)
        if queue == local_queue:
            with free_local_thread_lock:
                free_local_thread += 1
            #print "%s of %s local threads currently working" % (
            #    args.local_poolsize - free_local_thread, args.local_poolsize)
        time.sleep(0.1)
        print "%s of %s readcounts have been generated. %s/%s local thread. %s/%s external thread.\r"\
              %(num_finished,num_total,args.local_poolsize - free_local_thread, args.local_poolsize,
                args.external_poolsize - free_ext_thread, args.external_poolsize)
        queue.task_done()

init_free_space, space_difference = free_space_cal(args.allocated_space,args.allocated_space_unit)
progress_file_path, target_file_path = ready_paths()
ready_bam_files(progress_file_path)

for i in range(args.local_poolsize):
    covBed_thread = Thread(target=covBed_exe, args=(local_queue,))
    covBed_thread.daemon = True
    covBed_thread.start()
    time.sleep(0.1)
time.sleep(0.1)
for i in range(args.external_poolsize):
    covBed_thread = Thread(target=covBed_exe, args=(external_queue,))
    covBed_thread.daemon = True
    covBed_thread.start()
    time.sleep(0.1)

copy_file(copy_queue,init_free_space,space_difference)

copy_queue.join()
local_queue.join()
external_queue.join()