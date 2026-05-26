//#define NDEBUG
#include <chrono>
#include <fstream>
#include <iostream>
#include <string>
#include <string.h>
#include <queue>
#include <limits.h>
#include <iomanip>
#include <assert.h>
#include <math.h>

#ifndef DEEPOPT_BASIC_H
#define DEEPOPT_BASIC_H

using namespace std;

struct EDGE
{
	int v1;
	int v2;
};

enum STATE
{
	Candidate = 0,
	//Forbidden,
	Deleted,
	Fixed
	//InSol,
	//InSolStrong
};

struct ARRAY
{
	int* arr_;
	int* pos_;
	int size_;
	int capacity_;
	ARRAY(int capacity)
	{
		capacity_ = capacity;
		size_ = 0;
		arr_ = new int[capacity];
		pos_ = new int[capacity];
		memset(pos_, -1, capacity * sizeof(int));
	}
	~ARRAY()
	{
		delete[] pos_;
		delete[] arr_;
	}
	void push(int v)
	{
		arr_[size_] = v;
		pos_[v] = size_;
		size_++;
	}
	void pop(int v)
	{
		size_--;
		arr_[pos_[v]] = arr_[size_];
		pos_[arr_[size_]] = pos_[v];
		pos_[v] = -1;
	}
	void myClear()
	{
	    size_ = 0;
	    memset(pos_, -1, capacity_ * sizeof(int));
	}
};

chrono::steady_clock::time_point time_Start;
chrono::steady_clock::time_point round_time_Start;
chrono::steady_clock::time_point _round_time_Start;

double time_Sol;

long long step_Max;
long long Step;
int Seed;
int time_Cutoff;

int v_Num;
int e_Num;

EDGE* Edge;

int* v_Degree;
int* v_Weight;
int* v_Cost;
int* V_Cost_Origin; // just for check
int* v_State;
int** v_Adj;
int** v_Dmn;
int** v_Dmnd;
int* v_Dmn_size;
int* v_Dmnd_size;
int* v_Score;
int* v_Score_Real;

int* v_Num_Of_Dmnd;
int* v_Num_Of_Dmnd_Bak;
int* v_Dmnd_v1;
int* v_Dmnd_v2;

long long* v_Time_Stamp;

ARRAY* Undmnd;
ARRAY* Redundancy;

int* sol_Best;
int sol_Best_Size;
long long sol_Best_Cost;

ARRAY* sol_Tmp;
ARRAY* sol_Cur;
long long sol_Cur_Cost;
int gap;
int v_Cost_Max_In_Cand;

int* arr_Tmp; //arr_tmp
int arr_Tmp_Size;

int* cc;
int fix_Num;
int Pattern;

double getTimeElapsed()
{
	chrono::steady_clock::time_point time_now = chrono::steady_clock::now();
	chrono::duration<double> duration = time_now - time_Start;
	return duration.count();
}

double getRoundTimeElapsed()
{
	chrono::steady_clock::time_point time_now = chrono::steady_clock::now();
	chrono::duration<double> duration = time_now - round_time_Start;
	return duration.count();
}

double getLocalSearchTimeElapsed()
{
	chrono::steady_clock::time_point time_now = chrono::steady_clock::now();
	chrono::duration<double> duration = time_now - _round_time_Start;
	return duration.count();
}



int compare(int s1, int c1, int s2, int c2)
{
	if (c1 == c2)
	{
		if (s1 > s2)
			return 1;
		else if (s1 == s2)
			return 0;
		else
			return -1;
	}

	long long  t1 = s1, t2 = s2;
	t1 = t1 * c2;
	t2 = t2 * c1;
	if (t1 > t2)
		return 1;
	else if (t1 == t2)
		return 0;
	else
		return -1;
}

int comparePlus(int s1, int c1, int p1, int s2, int c2, int p2)
{

	if (c1 == c2)
	{
		if (s1 > s2 || (s1 == s2 && p1 > p2))
			return 1;
		else if (s1 == s2 && p1 == p2)
			return 0;
		else
			return -1;
	}
	long long t1 = s1, t2 = s2;
	t1 = t1 * c2;
	t2 = t2 * c1;
	if (t1 > t2 || (t1 == t2 && p1 > p2))
		return 1;
	else if (t1 == t2 && p1 == p2)
		return 0;
	else
		return -1;
}

int getAddVRand();
int getAddVBMS();
float ALPHA=0;
#endif
