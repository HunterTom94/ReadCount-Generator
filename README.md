ReadCount_Gen
=============

This script file is intended to easily generate readcount files from bam files 
using coverageBed. A target file for differential analysis using edgeR will also 
be prepared based on the generated readcounts. You can stop the work at anytime 
and restart the script. Progress of already finished files will be saved as long 
as the input and output folders remain unchanged. Multithreading and temporary
usage of local storage are supported if faster processing is needed and
hardware conditions allow it.

For a full utilization of the code, several inputs are needed:
copy_to_local - Set True if using local storage temporarily. Highly recommended
if a SSD is available and multithreading is enabled, since SSD's read speed
dramatically outweight external hard drive read speed. SSD's read speed will
not be a bottle neck when multithreading is enabled, while external hard
drive's will.

allocated_space - Amount of temporary storage space which will not be used by
ReadCount_Gen. If this parameter is unspecified, all available space in the
disc where temporary folder is located will be used. The units of the number
entered are specified with --allocated_space_unit

allocated_space_unit - Unit of allocated_space. Only accepts "MB" or "GB".

local_poolsize - Amount of threads used to process file from local temporary 
folder. Highly recommended if you have a powerful computer and SSD as temporary
local storage.

external_poolsize - Amount of threads used to process file from external hard
drive. Do not recommend integer higher than 4 since the relatively low read
speed will influence each thread's performance.

coverageBed_path - Full path of coverageBed executable file. If not specified,
script will assume coverageBed is in PATH.

bam_folder - Full path of folder containing original source of bam files. Can
accept multiple arguments separated by space, specify category in category
parameter. Bam files should be directly under the folder (not in subfolders).

category - Category of bam folders in the exact same order provided in
bam_folder parameter. Accept multiple arguments, separated by space.

bed_file - Full path of the bed file that is going to be used.

temp_folder - Full path of temporary folder, where bam files will be copied,
if temporary local storage is used. Folder will be created if not previously
exists.

output_folder - Full path of folder for readcount outputs, a progress file and a
target file that records task progress. Folder will be created if not
previously exists.

RNA_type - sno,lnc,piwi,etc..This string will be incoporated into output file
names.

A sample of comprehensive arguments are provided as below, for detailed
explaination of each parameters please use --help argument.

python2.7 path/to/script/ReadCount_Gen_args.py --copy_to_local True
--allocated_space 50 --allocated_space_unit GB --local_poolsize 13
--external_poolsize 2 --coverageBed_path /usr/local/bin/coverageBed
--bam_folder /media/huntertom/LaCie/Esophageal/miRNA_normal_BAM /media/huntertom/LaCie/Esophageal/miRNA_BAM 
--category normal Esophageal_Carcinoma 
--bed_file /home/huntertom/Downloads/NONCODEv4u1_human_ncRNAgrch37compat-3.bed
--temp_folder /home/huntertom/Documents/temp_bam
--output_folder /home/huntertom/Documents/Esophageal/piwi/test --RNA_type piwi

When using this script, please be aware that:
1. Python 2.7 is needed to run the script. Python 2.7 comes with Ubuntu.
2. This script does not support matched pair analysis so far. (tumor and normal
data from the same patients)
3. If normal hard drive is used as local storage, improvement of performance
over external hard drive has not be tested yet.
4. The sum of local_poolsize and external_poolsize is not advised to exceed the
total amount of logical cores available. In order to check number of available
logical core,
  * for PC users, refer to https://support.microsoft.com/en-us/instantanswers/64712e50-b59d-44f7-ab32-30264a4ed4fe/find-out-how-many-cores-your-processor-has
  * for Mac users, refer to http://stackoverflow.com/questions/1715580/how-to-discover-number-of-logical-cores-on-mac-os-x
  * for Linux users, refer to http://www.binarytides.com/linux-check-processor/
