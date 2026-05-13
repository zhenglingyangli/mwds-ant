#!/usr/bin/env python3

from subprocess import Popen, PIPE, STDOUT
import subprocess
import multiprocessing
from datetime import datetime
import os
import sys
import signal
import argparse
import csv
import time
import threading
import shutil

import psutil


def get_process_memory(proc):
    try:
        if sys.platform == 'linux':
            with open(f'/proc/{proc.pid}/status') as f:
                for line in f:
                    if 'VmHWM' in line:
                        return int(line.split()[1]) * 1024
        mem_info = proc.memory_full_info()
        return max(mem_info.uss, mem_info.rss)
    except:
        return 0


def memory_monitor(process, stop_event, peak_memory, cutoff_mem_mb, process_status):
    try:
        sampling_interval = 0.01
        termination_grace_period = 0.1

        while not stop_event.is_set():
            try:
                current_memory = get_process_memory(process) / 1024 / 1024
                if current_memory > 0:
                    peak_memory[0] = max(peak_memory[0], current_memory)
                    if current_memory < 1:
                        time.sleep(0.001)
                        current_memory = get_process_memory(process) / 1024 / 1024
                        if current_memory > 0:
                            peak_memory[0] = max(peak_memory[0], current_memory)

                if cutoff_mem_mb and current_memory > cutoff_mem_mb:
                    try:
                        process_status[0] = "pending_termination"
                        final_memory = get_process_memory(process) / 1024 / 1024
                        peak_memory[0] = max(peak_memory[0], final_memory)
                        time.sleep(termination_grace_period)
                        process.kill()
                        for child in process.children(recursive=True):
                            try:
                                child_final_memory = get_process_memory(child) / 1024 / 1024
                                peak_memory[0] = max(peak_memory[0], child_final_memory)
                                child.kill()
                            except:
                                continue
                    except psutil.NoSuchProcess:
                        pass
                    process_status[0] = "out_of_mem"
                    stop_event.set()
                    print("Memory limit exceeded")
                    break

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break

            time.sleep(sampling_interval)

    except Exception as e:
        print(f"Memory monitoring error: {str(e)}")
    finally:
        try:
            additional_monitoring_time = 0.2
            monitoring_interval = 0.01
            iterations = int(additional_monitoring_time / monitoring_interval)
            for _ in range(iterations):
                try:
                    final_memory = get_process_memory(process) / 1024 / 1024
                    if final_memory > 0:
                        peak_memory[0] = max(peak_memory[0], final_memory)
                except:
                    break
                time.sleep(monitoring_interval)
        except:
            pass


def output_monitor(process, output_file, stop_event):
    with open(output_file, 'w', buffering=1) as f:
        try:
            for line in iter(process.stdout.readline, ''):
                if line == '':
                    break
                f.write(line)
                f.flush()

        except Exception as e:
            print(f"Error in output monitor: {str(e)}")

        finally:
            try:
                remaining_output = process.stdout.read()
                if remaining_output:
                    f.write(remaining_output)
                    f.flush()
            except Exception:
                pass


def terminate_process_tree(parent_pid):
    try:
        parent = psutil.Process(parent_pid)
        children = parent.children(recursive=True)
        for child in children:
            try:
                child.kill()
            except psutil.NoSuchProcess:
                pass
        parent.kill()
    except psutil.NoSuchProcess:
        pass


def worker(id, solver, instance, output_dir, cutoff_time, cutoff_mem, additional_args):
    print("[{}] Starting benchmark on {}".format(id + 1, os.path.basename(instance)))

    instance_name = os.path.basename(instance)
    output_file = os.path.join(output_dir, "{}.out".format(instance_name))

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    open(output_file, 'w').close()

    if additional_args and isinstance(additional_args[0], (list, tuple)):
        additional_args = additional_args[0]

    if solver.endswith('.py'):
        cmd = ['python', solver, instance] + list(additional_args)
    else:
        cmd = [solver, instance] + list(additional_args)
        # C/C++ solvers use block buffering when stdout is piped. Without
        # line buffering, a timeout kill can lose the latest LB/UB round lines.
        if shutil.which('stdbuf'):
            cmd = ['stdbuf', '-oL', '-eL'] + cmd

    peak_memory = [0]
    process_status = ["completed"]
    stop_event = threading.Event()
    solver_time = [0]

    cutoff_mem_mb = cutoff_mem * 1024 if cutoff_mem else None

    start_time = time.perf_counter()
    process = None

    try:
        process = Popen(
            cmd,
            stdout=PIPE,
            stderr=STDOUT,
            universal_newlines=True,
            bufsize=1,
            env={**os.environ, 'PYTHONUNBUFFERED': '1'}
        )
        psutil_process = psutil.Process(process.pid)

        monitor_thread = threading.Thread(
            target=memory_monitor,
            args=(psutil_process, stop_event, peak_memory, cutoff_mem_mb, process_status)
        )
        monitor_thread.start()

        output_thread = threading.Thread(
            target=output_monitor,
            args=(process, output_file, stop_event)
        )
        output_thread.start()

        def kill_process():
            try:
                process_status[0] = "out_of_time"
                solver_time[0] = cutoff_time
                if process and process.pid:
                    terminate_process_tree(process.pid)
            finally:
                stop_event.set()
                print("Timeout for {}".format(instance_name))

        signal.signal(signal.SIGALRM, lambda signum, frame: kill_process())
        signal.alarm(cutoff_time)

        try:
            process.wait()
        finally:
            signal.alarm(0)

            if process and process.poll() is None:
                terminate_process_tree(process.pid)
                try:
                    process.wait(timeout=1)
                except:
                    pass

            output_thread.join(timeout=5)
            stop_event.set()
            monitor_thread.join()

    except Exception as e:
        print(f"Error in worker: {str(e)}")
        if process and process.poll() is None:
            terminate_process_tree(process.pid)

    finally:
        solver_time[0] = time.perf_counter() - start_time

    print("[{}] Finished benchmark on {}".format(id + 1, os.path.basename(instance)))

    # Append a >>> summary line on timeout/OOM so sumup can still collect the record
    if process_status[0] in ("out_of_time", "out_of_mem"):
        status = "TIMEOUT" if process_status[0] == "out_of_time" else "MEMOUT"
        timeout_line = (
            f">>> Benchmark {instance_name} "
            f"Status {status} "
            f"TimeTotal {cutoff_time:.3f}\n"
        )
        try:
            with open(output_file, 'a') as f:
                f.write(timeout_line)
        except Exception:
            pass

    if process_status[0] == "out_of_mem":
        return instance_name, "out_of_mem", solver_time[0]
    elif process_status[0] == "out_of_time":
        return instance_name, peak_memory[0], "out_of_time"
    else:
        return instance_name, peak_memory[0], solver_time[0]


def write_time_and_memory_csv(output_dir, benchmark_data, prefix):
    csv_file = os.path.join(output_dir, f"time_and_memory-{prefix}.csv")
    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Instance", "PeakMem(MB)", "Time(s)"])
        for instance, peak_mem, exec_time in benchmark_data:
            peak_mem_str = f"{peak_mem:.2f}" if isinstance(peak_mem, (int, float)) else peak_mem
            exec_time_str = f"{exec_time:.2f}" if isinstance(exec_time, (int, float)) else exec_time
            writer.writerow([instance, peak_mem_str, exec_time_str])


def read_name_list(name_list_file):
    with open(name_list_file, 'r') as f:
        return set(line.strip() for line in f)


def get_item_under_dir(inputPath, allowed_names=None):
    instances = []
    for item in os.listdir(inputPath):
        item_path = os.path.join(inputPath, item)
        if os.path.isfile(item_path) and (allowed_names is None or os.path.basename(item_path) in allowed_names):
            instances.append(item_path)
        elif os.path.isdir(item_path):
            instances.extend(get_item_under_dir(item_path, allowed_names))
    return instances


def goSolver(nbCPU, cutoffTime, cutoffMem, solver, inputPath, outputRoot, name_list_file, suffix, *additional_args):
    solver_name = os.path.splitext(os.path.basename(solver))[0]
    dataset_name = os.path.basename(os.path.normpath(inputPath))

    allowed_names = read_name_list(name_list_file) if name_list_file else None

    if not os.path.exists(inputPath):
        print("Input path does not exist.")
        return

    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')

    if suffix:
        output_dir = os.path.join(outputRoot, f"result-{solver_name}-{dataset_name}-{suffix}-{timestamp}")
    else:
        output_dir = os.path.join(outputRoot, f"result-{solver_name}-{dataset_name}-{timestamp}")

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    instances = []
    if os.path.isdir(inputPath):
        for item in os.listdir(inputPath):
            item_path = os.path.join(inputPath, item)
            if os.path.isfile(item_path) and (allowed_names is None or os.path.basename(item_path) in allowed_names):
                instances.append(item_path)
            elif os.path.isdir(item_path):
                instances.extend(get_item_under_dir(item_path, allowed_names))
    else:
        instances.append(inputPath)

    pool = multiprocessing.Pool(nbCPU)
    jobs = []
    for id, instance in enumerate(instances):
        jobs.append(
            pool.apply_async(worker, (id, solver, instance, output_dir, cutoffTime, cutoffMem, additional_args)))

    benchmark_data = []
    for job in jobs:
        instance_name, peak_mem, exec_time = job.get()
        benchmark_data.append((instance_name, peak_mem, exec_time))

    pool.close()
    pool.join()

    out_suffix = f"{solver_name}_{dataset_name}" + (suffix if suffix is not None else "")
    write_time_and_memory_csv(output_dir, benchmark_data, out_suffix)

    print("All benchmarks are completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run goSolver with specified parameters.")
    parser.add_argument("nbCPU", type=int, help="Number of CPUs to use")
    parser.add_argument("cutoffTime", type=int, help="Cutoff time in seconds")
    parser.add_argument("solver", help="Solver to use")
    parser.add_argument("inputPath", help="Path to input file")
    parser.add_argument("outputRoot", help="Root for output files")

    parser.add_argument("--cutoff_mem", type=float, help="Memory limit in GB", default=None)
    parser.add_argument("--name_list", help="Path to a text file containing allowed file names")
    parser.add_argument("--suffix", help="Suffix for the generated result directory")

    args, solver_args = parser.parse_known_args()

    goSolver(args.nbCPU, args.cutoffTime, args.cutoff_mem, args.solver, args.inputPath, args.outputRoot,
             args.name_list, args.suffix, solver_args)
