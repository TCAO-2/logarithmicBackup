# Copyright (c) 2023 Raphaël MARTIN
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# This script is adapted from Neil Fraser and Christopher Allen logarithmic backup algorithm.
# It offers a compromise in the conservation of backups,
# with close for recent ones while a long history is covered.
#
# https://neil.fraser.name/software/backup/










########################################################################
# Import dependencies
########################################################################

from os import listdir
import subprocess
from time import time, strptime, mktime
from datetime import datetime
import argparse
import logging










########################################################################
# Constants
########################################################################

TIMESTAMP_FORMAT = "%Y-%m-%d_%H-%M-%S"

SCRIPT_PARAMETERS = {
    "src_dir": {
        "short_arg": "s",
        "type": str,
        "required": True,
        "help": "source directory path",
        "default": None # There is no default value as this parameter is required.
    },
    "bkp_dir": {
        "short_arg": "b",
        "type": str,
        "required": True,
        "help": "destination directory path",
        "default": None # There is no default value as this parameter is required.
    },
    "bkp_prefix": {
        "short_arg": "p",
        "type": str,
        "required": False,
        "help": "backup name prefix",
        "default": "backup"
    },
    "expected_bkp_interval_sec": {
        "short_arg": "i",
        "type": int,
        "required": False,
        "help": "expected time between regular backup events",
        "default": 3600 # 1 day
    },
    "max_bkp_kept": {
        "short_arg": "m",
        "type": int,
        "required": False,
        "help": "maximum amount of backups kept",
        "default": 14
    },
    "outdated_bkp_sec": {
        "short_arg": "o",
        "type": int,
        "required": False,
        "help": "time for which a backup is outdated",
        "default": 2457600 # 2 years
    },
    "compress": {
        "short_arg": "c",
        "type": bool,
        "required": False,
        "help": "compress backups",
        "default": False
    }
}










########################################################################
# Get script passed parameters
########################################################################

def get_script_parameters() -> argparse.Namespace:
    # I use argparse to manage script parameters, SCRIPT_PARAMETERS defines each
    parser = argparse.ArgumentParser()
    for key, value in SCRIPT_PARAMETERS.items():
        parser.add_argument(
            f"-{value['short_arg']}",
            f"--{key}",
            type=value['type'],
            required=value['required'],
            help=value['help'],
            default=value['default']
        )
    args = parser.parse_args()
    return args










########################################################################
# Subprocess execution
########################################################################

class SubprocessFailedError(Exception):
    pass

def run_subprocess(cmd: str) -> str:
    cmd_args = cmd.split(" ")
    with subprocess.Popen(cmd_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as pipe:
        std_out, std_err = pipe.communicate()
        std_out_msg = std_out.decode("utf-8")[:-1] # Removed the last \n char.
        std_err_msg = std_err.decode("utf-8")[:-1]
        return_code = pipe.returncode
        if (return_code == 0):
            # The command has run as expected.
            return return_code, std_out_msg, std_err_msg
        else:
            # The command has failed.
            raise SubprocessFailedError(return_code, std_out_msg, std_err_msg)










########################################################################
# Backup files manipulation
########################################################################

class BackupFilesManipulator:

    def __init__(self, src_dir: str, bkp_dir: str, bkp_prefix: str, compress: bool) -> None:
        self.src_dir = src_dir
        self.bkp_dir = bkp_dir
        # bkp_prefix is used to recognize multiple bkps in the same dir.
        self.bkp_prefix = bkp_prefix
        self.compress = compress
        if self.compress:
            self.bkp_suffix = "tar.gz"
        else:
            self.bkp_suffix = "tar"
        # Compute date char indexes for filenames checking.
        self.filename_date_start_index = len(self.bkp_prefix) + 1
        self.filename_date_stop_index = -1 * (len(self.bkp_suffix) + 1)

    def is_bkp_file(self, filename: str) -> bool:
        # Returns True if the filename is like bkp_prefix_YY-mm-dd_HH-MM-SS.bkp_suffix
        if filename.startswith(self.bkp_prefix) and filename.endswith(self.bkp_suffix):
            str_date = filename[self.filename_date_start_index : self.filename_date_stop_index]
            try:
                strptime(str_date, TIMESTAMP_FORMAT)
                return True
            except:
                return False
        else:
            return False

    def get_bkp_filenames(self) -> [str]:
        # Returns a list of filenames from the bkp_dir whose names correspond to backups
        try:
            filenames = listdir(self.bkp_dir)
            bkp_filenames = [filename for filename in filenames if self.is_bkp_file(filename)]
            return bkp_filenames
        except FileNotFoundError as err:
            logging.error(f"Failed to list backup filesnames in {self.bkp_dir}\n\t{err}")

    def get_file_timestamp_from_filename(self, filename: str) -> int:
        # Returns timestamp from bkp_prefix_YY-mm-dd_HH-MM-SS.bkp_suffix
        str_date = filename[self.filename_date_start_index : self.filename_date_stop_index]
        struct_time = strptime(str_date, TIMESTAMP_FORMAT)
        timestamp = mktime(struct_time)
        return timestamp

    def get_bkp_filename_from_timestamp(self, timestamp: int) -> str:
        # Returns bkp_prefix_YY-mm-dd_HH-MM-SS.bkp_suffix from timestamp.
        struct_time = datetime.fromtimestamp(timestamp)
        date = struct_time.strftime(TIMESTAMP_FORMAT)
        filename = f"{self.bkp_prefix}_{date}.{self.bkp_suffix}"
        return filename

    def get_bkp_timestamps_from_filenames(self, bkp_filenames: [str]) -> [float]:
        return [self.get_file_timestamp_from_filename(filename) for filename in bkp_filenames]

    def get_number_of_bkp(self) -> int:
        try:
            return len(self.get_bkp_filenames())
        except:
            return 0

    def archive(self) -> None:
        timestamp = time()
        bkp_filename = self.get_bkp_filename_from_timestamp(timestamp)
        bkp_target = f"{self.bkp_dir}/{bkp_filename}"
        if self.compress:
            command = f"tar -czf {bkp_target} -C {self.src_dir} ."
        else:
            command = f"tar -cf {bkp_target} -C {self.src_dir} ."
        try:
            run_subprocess(command)
            logging.info(f"Backuped {self.src_dir} into {bkp_target}")
        except SubprocessFailedError as err:
            logging.error(f"Failed to backup {self.src_dir} into {bkp_target}\n\t{err}")

    def rm_bkp_file(self, bkp_filename: str) -> None:
        bkp_target = f"{self.bkp_dir}/{bkp_filename}"
        command = f"rm {bkp_target}"
        try:
            run_subprocess(command)
            logging.info(f"Removed backup {bkp_target}")
        except SubprocessFailedError as err:
            logging.error(f"Failed to remove backup {bkp_target}\n\t{err}")










########################################################################
# Backup cleaning evaluation
########################################################################

class BackupCleaningEvaluator:

    def __init__(self, max_bkp_kept: int) -> None:
        self.max_bkp_kept = max_bkp_kept

    def is_bkp_remove_needed(self, number_of_bkp: int) -> bool:
        return number_of_bkp > self.max_bkp_kept

    def evaluator_older_bkp_index(self, bkp_timestamps: [float],
            outdated_bkp_sec: int) -> int or None:
        # Returns the older_bkp if bkp_timestamps (sec) has been reached.
        current_time = time()
        bkp_timestamp = min(bkp_timestamps)
        if current_time - bkp_timestamp > outdated_bkp_sec:
            return bkp_timestamps.index(bkp_timestamp)

    def evaluator_log_bkp_index(self, bkp_timestamps: [float], expect_interval: int) -> int:
        current_time = time()
        # The desired number of backups.
        backup_count = len(bkp_timestamps) - 1
        # The total date range between now and the oldest backup.
        total_time = current_time - bkp_timestamps[0]
        # The number of backups that have been deleted or not present.
        missing = max(total_time / expect_interval - backup_count, 0)
        # A decay rate of 2.0 would dictate that each archived
        # backup would ideally be twice the age of its predecessor.
        decay_rate = (missing + 1) ** (1 / backup_count)
        # An array of time stamps that the backups should have.
        ideal_times = []
        for n in range(len(bkp_timestamps) - 1, -1, -1):
            value = current_time - expect_interval * (n + (decay_rate**n) - 1)
            ideal_times.append(value)
        # As we have bkp_timestamps and ideal_times,
        # we have to find the backup to delete to fit the ideal_times.
        # Then we compute cumulative errors from right then from left,
        # the least projected_error (right error + left error)
        # gives the backup to remove.
        right_diff = [abs(bkp_timestamps[-1] - ideal_times[-1])]
        for n in range(len(bkp_timestamps) - 2, -1, -1):
            value = abs(bkp_timestamps[n] - ideal_times[n]) + right_diff[0]
            right_diff.insert(0, value)
        left_diff = [0]
        for n in range(1, len(bkp_timestamps)):
            value = abs(bkp_timestamps[n-1] - ideal_times[n]) + left_diff[-1]
            left_diff.append(value)
        projected_error = []
        for n in range(len(bkp_timestamps) - 1):
            value = left_diff[n] + right_diff[n+1]
            projected_error.append(value)
        bkp_timestamp = min(projected_error[1:])
        bkp_timestamp_index = projected_error.index(bkp_timestamp)
        return bkp_timestamp_index










########################################################################
# Backup strategy
########################################################################

class BackupHandler:

    def __init__(self, src_dir: str, bkp_dir: str,
            bkp_prefix=SCRIPT_PARAMETERS["bkp_prefix"]["default"],
            compress=SCRIPT_PARAMETERS["compress"]["default"],
            max_bkp_kept=SCRIPT_PARAMETERS["max_bkp_kept"]["default"],
            bkp_timestamps=SCRIPT_PARAMETERS["outdated_bkp_sec"]["default"],
            interval=SCRIPT_PARAMETERS["expected_bkp_interval_sec"]["default"]) -> None:
        self.bkp_files_manipulator = BackupFilesManipulator(src_dir, bkp_dir,
            bkp_prefix, compress)
        self.max_bkp_kept = max_bkp_kept
        self.bkp_cleaning_evaluator = BackupCleaningEvaluator(self.max_bkp_kept)
        self.bkp_timestamps = bkp_timestamps
        self.interval = interval

    def get_bkp_filenames_to_clean(self) -> [str]:
        number_of_bkp = self.bkp_files_manipulator.get_number_of_bkp()
        number_of_bkp_to_clean = max(number_of_bkp - self.max_bkp_kept, 0)
        if (number_of_bkp_to_clean == 0):
            return []
        else:
            bkp_filenames = self.bkp_files_manipulator.get_bkp_filenames()
            bkp_timestamps = self.bkp_files_manipulator.get_bkp_timestamps_from_filenames(
                bkp_filenames)
            bkp_filenames_to_clean = []
            for i in range(number_of_bkp_to_clean):
                # If there are outdated backups, clean the oldest one,
                # else clean via the logarithmic evaluator.
                index_to_delete = self.bkp_cleaning_evaluator.evaluator_older_bkp_index(
                    bkp_timestamps, self.bkp_timestamps)
                if index_to_delete is None:
                    index_to_delete = self.bkp_cleaning_evaluator.evaluator_log_bkp_index(
                        bkp_timestamps, self.interval)
                bkp_filenames_to_clean.append(bkp_filenames.pop(index_to_delete))
                bkp_timestamps.pop(index_to_delete)
            return bkp_filenames_to_clean

    def archive(self) -> None:
        self.bkp_files_manipulator.archive()

    def clean_bkp_dir(self) -> None:
        bkp_filenames_to_clean = self.get_bkp_filenames_to_clean()
        for filename in bkp_filenames_to_clean:
            self.bkp_files_manipulator.rm_bkp_file(filename)










########################################################################
# Main execution
########################################################################

def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    args = get_script_parameters()
    bkp_handler = BackupHandler(args.src_dir, args.bkp_dir, compress=args.compress)
    bkp_handler.archive()
    bkp_handler.clean_bkp_dir()

if __name__ == '__main__':
	main()
