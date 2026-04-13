#include "maxheap.h"
#include "lb-search-util.h"
#include "util_vector.h"
//#include <climits>

void freeAll()
{
	for (int i = 0; i <= v_Num; ++i)
	{
		delete[] v_Adj[i];
		delete[] v_Dmnd[i];
	}
	delete[] cc;
	delete[] arr_Tmp;
	delete[] sol_Best;
	delete sol_Tmp;
	delete sol_Cur;
	delete Redundancy;
	delete Undmnd;
	delete[] v_Dmnd_v2;
	delete[] v_Dmnd_v1;
	delete[] v_Time_Stamp;
	delete[] v_Num_Of_Dmnd;
	//delete[] v_Score_Real;
	delete[] v_Score;
	delete[] v_Dmnd_size;
	delete[] v_Dmn_size;
	delete[] v_Dmnd;
	delete[] v_Adj;
	delete[] v_State;
	delete[] V_Cost_Origin;
	delete[] v_Cost;
	delete[] v_Weight;
	delete[] v_Degree;
}


int readGraph(string file_name)
{
	int v1, v2;
	string string_sign, string_tmp;
	ifstream file_ifs(file_name);

	if (file_ifs.fail())
	{
		cout << "### Error Open, File Name: " << file_name << endl;
		return 1;
	}

	while (file_ifs.peek() != 'p')
		getline(file_ifs, string_tmp);

	file_ifs >> string_sign >> string_tmp >> v_Num >> e_Num;

	Edge = new EDGE[e_Num + 1];
	v_Degree = new int[v_Num + 1];
	v_Weight = new int[v_Num + 1];
	v_Cost = new int[v_Num + 1];
	V_Cost_Origin = new int[v_Num + 1];
	v_State = new int[v_Num + 1];
	v_Adj = new int* [v_Num + 1];
	v_Dmnd = new int* [v_Num + 1];
	v_Dmn_size = new int[v_Num + 1];
	v_Dmnd_size = new int[v_Num + 1];
	v_Score = new int[v_Num + 1];
	//v_Score_Real = new int[v_Num + 1];
	v_Num_Of_Dmnd = new int[v_Num + 1];
	v_Num_Of_Dmnd_Bak = new int[v_Num + 1]; // I am here!
	v_Time_Stamp = new long long[v_Num + 1];
	v_Dmnd_v1 = new int[v_Num + 1];
	v_Dmnd_v2 = new int[v_Num + 1];
	Undmnd = new ARRAY(v_Num + 1);
	Redundancy = new ARRAY(v_Num + 1);
	sol_Cur = new ARRAY(v_Num + 1);
	sol_Tmp = new ARRAY(v_Num + 1);
	sol_Best = new int[v_Num + 1];
	arr_Tmp = new int[v_Num + 1];
	cc = new int[v_Num + 1];

	double dense = 2.0 * e_Num / (double)v_Num / (double)(v_Num - 1);

	if (dense > 0.07)
		Pattern = 1;
	else Pattern = 0;

	memset(v_Degree, 0, (v_Num + 1) * sizeof(int));

	file_ifs >> string_sign >> v1 >> v2;
	//while(string_sign == "v")
	//file_ifs >> string_sign >> v1 >> v2;
	if (string_sign == "v")
	{
		v_Cost[v1] = v2;
		for (int i = 2; i <= v_Num; ++i)
		{
			file_ifs >> string_sign >> v1 >> v2;
			v_Cost[v1] = v2;
		}
		file_ifs >> string_sign >> v1 >> v2;
	}
	else
	{
		for (int i = 1; i <= v_Num; ++i)
		{
			//v_Cost[i] = 1;
			v_Cost[i] = i % 200 + 1;
		}
	}

	
	v_Degree[v1]++;
	v_Degree[v2]++;
	Edge[1].v1 = v1;
	Edge[1].v2 = v2;
	for (int i = 2; i <= e_Num; ++i)
	{
		file_ifs >> string_tmp >> v1 >> v2;
		//v1--;
		//v2--;
		v_Degree[v1]++;
		v_Degree[v2]++;
		Edge[i].v1 = v1;
		Edge[i].v2 = v2;
	}
	for (int i = 1; i <= v_Num; ++i)
	{
		v_Adj[i] = new int[v_Degree[i] + 1];
		v_Dmnd[i] = new int[v_Degree[i] + 1];//vertex be solely domed by i
		v_Degree[i] = 0;
	}
	for (int i = 1; i <= e_Num; ++i)
	{
		v1 = Edge[i].v1;
		v2 = Edge[i].v2;
		assert(v1>=1 && v2>=1);
		if(v1==v2)
		  continue;
		int j=0;
		for(j=0;j<v_Degree[v1];j++){
                  if(v_Adj[v1][j] == v2)
		    break;
		}
		if(j==v_Degree[v1]){
		  v_Adj[v1][v_Degree[v1]++] = v2;
		  v_Adj[v2][v_Degree[v2]++] = v1;
		}
	}

/*
	int degree_max = -1;
	for(int i = 1; i <= v_Num; ++i)
		if(degree_max < v_Degree[i])
			degree_max = v_Degree[i];

	for(int i = 1; i <= v_Num; ++i)
	{
		if(v_Degree[i] > 0.85 * degree_max)
			v_Cost[i] = 1;
		else if(v_Degree[i] > 0.6 * degree_max)
			v_Cost[i] = 2;
		else if(v_Degree[i] > 0.35 * degree_max)
			v_Cost[i] = 4;
		else 
			v_Cost[i] = 8;
	}
*/
	for (int i = 1; i <= v_Num; ++i)
	{
		V_Cost_Origin[i] = v_Cost[i];
	}
	_read_graph_wclq_format(v_Num,e_Num, v_Degree, v_Adj,v_Cost);
	
	delete[] Edge;
	return 0;
}


void newAddVertexInit(int v_add)
{
	int i, j;
	int v_n, v_n_n;
	int score_add = v_Score[v_add];
	//int score_real_add = v_Score_Real[v_add];
	
	sol_Cur->push(v_add);
	sol_Cur_Cost += v_Cost[v_add];
	v_Time_Stamp[v_add] = Step;

	for (i = 0; i < v_Dmn_size[v_add]; ++i)
	{
		v_n = v_Dmn[v_add][i];
		v_Num_Of_Dmnd[v_n]++;
		if (v_Num_Of_Dmnd[v_n] == 1)
		{
			for (j = 0; j < v_Dmnd_size[v_n]; ++j)
			{
				v_n_n = v_Dmnd[v_n][j];
				v_Score[v_n_n] -= v_Weight[v_n];
				//v_Score_Real[v_n_n] -= 1;
				//if (v_n_n != v_add)
				//	max_heap->changeVal(v_n_n);
			}
			v_Dmnd_v1[v_n] = v_add;
			Undmnd->pop(v_n);
		}
		else if (v_Num_Of_Dmnd[v_n] == 2)
		{
			v_n_n = v_Dmnd_v1[v_n];
			v_Score[v_n_n] += v_Weight[v_n];
			//v_Score_Real[v_n_n] += 1;
			if (v_Score[v_n_n] == 0 && Redundancy->pos_[v_n_n] == -1)
				Redundancy->push(v_n_n);
			v_Dmnd_v2[v_n] = v_add;
		}
	}
	v_Score[v_add] = -score_add;
	//v_Score_Real[v_add] = -score_real_add;
}


void addVertexInit(int v_add, MAXHEAP* max_heap)
{
	int i, j;
	int v_n, v_n_n;
	int score_add = v_Score[v_add];
	//int score_real_add = v_Score_Real[v_add];
	
	sol_Cur->push(v_add);
	sol_Cur_Cost += v_Cost[v_add];
	v_Time_Stamp[v_add] = Step;

	for (i = 0; i < v_Dmn_size[v_add]; ++i)
	{
		v_n = v_Dmn[v_add][i];
		v_Num_Of_Dmnd[v_n]++;
		if (v_Num_Of_Dmnd[v_n] == 1)
		{
			for (j = 0; j < v_Dmnd_size[v_n]; ++j)
			{
				v_n_n = v_Dmnd[v_n][j];
				v_Score[v_n_n] -= v_Weight[v_n];
				//v_Score_Real[v_n_n] -= 1;
				if (v_n_n != v_add)
					max_heap->changeVal(v_n_n);
			}
			v_Dmnd_v1[v_n] = v_add;
			Undmnd->pop(v_n);
		}
		else if (v_Num_Of_Dmnd[v_n] == 2)
		{
			v_n_n = v_Dmnd_v1[v_n];
			v_Score[v_n_n] += v_Weight[v_n];
			//v_Score_Real[v_n_n] += 1;
			if (v_Score[v_n_n] == 0 && Redundancy->pos_[v_n_n] == -1)
				Redundancy->push(v_n_n);
			v_Dmnd_v2[v_n] = v_add;
		}
	}
	v_Score[v_add] = -score_add;
	//v_Score_Real[v_add] = -score_real_add;
}

void addVertex(int v_add)
{
	int i, j;
	int v_n, v_n_n;
	int score_add = v_Score[v_add];
	//int score_add_real = v_Score_Real[v_add];
	
	sol_Cur->push(v_add);
	sol_Cur_Cost += v_Cost[v_add];
	v_Time_Stamp[v_add] = Step;

	if (Pattern == 1)
		gap = sol_Cur_Cost / sol_Cur->size_;
	else if (Pattern == 0)
	{
		if (v_Cost[v_add] > v_Cost[v_Cost_Max_In_Cand])
		{
			v_Cost_Max_In_Cand = v_add;
			gap = v_Cost[v_Cost_Max_In_Cand];
		}
	}
	

	for (i = 0; i < v_Dmn_size[v_add]; ++i)
	{
		v_n = v_Dmn[v_add][i];
		v_Num_Of_Dmnd[v_n]++;
		for (j = 0; j < v_Dmnd_size[v_n]; ++j)
			if (cc[v_Dmnd[v_n][j]] == 0)
				cc[v_Dmnd[v_n][j]] = 1;
		if (v_Num_Of_Dmnd[v_n] == 1)
		{
			for (j = 0; j < v_Dmnd_size[v_n]; ++j)
			{
				v_n_n = v_Dmnd[v_n][j];
				v_Score[v_n_n] -= v_Weight[v_n];
				//v_Score_Real[v_n_n] -= 1;
			}
			v_Dmnd_v1[v_n] = v_add;
			Undmnd->pop(v_n);
		}
		else if (v_Num_Of_Dmnd[v_n] == 2)
		{
			v_n_n = v_Dmnd_v1[v_n];
			v_Score[v_n_n] += v_Weight[v_n];
			//v_Score_Real[v_n_n] += 1;
			if (v_Score[v_n_n] == 0 && Redundancy->pos_[v_n_n] == -1)
				Redundancy->push(v_n_n);
			v_Dmnd_v2[v_n] = v_add;
		}
	}
	for (i = 0; i < v_Dmn_size[v_add]; ++i)
		cc[v_Dmn[v_add][i]] = 1;
	v_Score[v_add] = -score_add;
	//v_Score_Real[v_add] = -score_add_real;
}

void removeVertex(int v_remove)
{
	int i, j;
	int v_n, v_n_n;
	int score_remove = v_Score[v_remove];
	//int score_remove_real = v_Score_Real[v_remove];
	
	sol_Cur->pop(v_remove);
	sol_Cur_Cost -= v_Cost[v_remove];
	v_Time_Stamp[v_remove] = Step;


	if (sol_Cur->size_ == 0)
		gap = 0;
	else if (Pattern == 1)
	{
		gap = sol_Cur_Cost / sol_Cur->size_;
	}
	else if (v_remove == v_Cost_Max_In_Cand)
	{
		v_Cost_Max_In_Cand = sol_Cur->arr_[0];
		for (i = 1; i < sol_Cur->size_; ++i)
			if (v_Cost[sol_Cur->arr_[i]] > v_Cost[v_Cost_Max_In_Cand])
				v_Cost_Max_In_Cand = sol_Cur->arr_[i];
		gap = v_Cost[v_Cost_Max_In_Cand];
	}

	if (Redundancy->pos_[v_remove] != -1 && v_Score[v_remove] == 0)
		Redundancy->pop(v_remove);

	for (i = 0; i < v_Dmn_size[v_remove]; ++i)
	{
		v_n = v_Dmn[v_remove][i]; // v_n that is dmnd by v_remove
		v_Num_Of_Dmnd[v_n]--;
		for (j = 0; j < v_Dmnd_size[v_n]; ++j)
			if (cc[v_Dmnd[v_n][j]] == 0)
				cc[v_Dmnd[v_n][j]] = 1;
		if (v_Num_Of_Dmnd[v_n] == 2)
		{
			int flag = 0;
			for (j = 0; j < v_Dmnd_size[v_n]; ++j)
			{
				v_n_n = v_Dmnd[v_n][j];
				if (sol_Cur->pos_[v_n_n] != -1)
				{
					if (flag == 0)
					{
						v_Dmnd_v1[v_n] = v_n_n;
						flag = 1;
					}
					else
					{
						v_Dmnd_v2[v_n] = v_n_n;
						break;
					}
				}
			}
		}
		else if (v_Num_Of_Dmnd[v_n] == 1)
		{
			if (v_Dmnd_v1[v_n] == v_remove)
				v_Dmnd_v1[v_n] = v_Dmnd_v2[v_n];
			v_n_n = v_Dmnd_v1[v_n];
			v_Score[v_n_n] -= v_Weight[v_n];
			//v_Score_Real[v_n_n] -= 1;
			if (Redundancy->pos_[v_n_n] != -1 && v_Score[v_n_n] != 0)
				Redundancy->pop(v_n_n);
		}
		else if (v_Num_Of_Dmnd[v_n] == 0)
		{
			for (j = 0; j < v_Dmnd_size[v_n]; ++j)
			{
				v_n_n = v_Dmnd[v_n][j];
				v_Score[v_n_n] += v_Weight[v_n];
				//v_Score_Real[v_n_n] += 1;
				cc[v_n_n] = 2;
			}
			Undmnd->push(v_n);
		}
	}
	v_Score[v_remove] = -score_remove;
	//v_Score_Real[v_remove] = -score_remove_real;
	cc[v_remove] = 0;
}

void reduceGraph()
{
	memset(v_State, 0, (v_Num + 1) * sizeof(int));
	for (int v = 1; v <= v_Num; ++v)
	{
		if (v_Degree[v] == 0)
		{
			v_State[v] = STATE::Fixed;
			continue;
		}
		if (v_Degree[v] == 1)
		{
			int v_n = v_Adj[v][0];
			if (v_State[v_n] > 0 || v_State[v] > 0)
				continue;
			if (v_Cost[v] >= v_Cost[v_n])
			{
				v_State[v_n] = STATE::Fixed;
				v_State[v] = STATE::Deleted;
			}
			else // cost v < cost v_n
			{
				if (v_Degree[v_n] == 1)
				{
					v_State[v] = STATE::Fixed;
					v_State[v_n] = STATE::Deleted;
				}
				else
				{
					v_State[v] = v_n + 10;
					v_Cost[v_n] -= v_Cost[v];
				}
			}
			continue;
		}
		if (v_Degree[v] == 2)
		{
			int v_n1 = v_Adj[v][0];
			int v_n2 = v_Adj[v][1];
			if (v_State[v] > 0 || v_State[v_n1] > 0 || v_State[v_n2] > 0) // check
				continue;
			int v_a, v_b, v_c;
			if (v_Degree[v_n1] == 2)
			{
				v_a = v_n1;
				v_b = v_n2;
			}
			else if (v_Degree[v_n2] == 2)
			{
				v_a = v_n2;
				v_b = v_n1;
			}
			else
				continue;
			if (v_Adj[v_a][0] == v)
				v_c = v_Adj[v_a][1];
			else
				v_c = v_Adj[v_a][0];
			if (v_c == v_b) // v degree 2; v_a degree 2; v_b(v_c) degree >= 2;
			{
				if (v_Cost[v_b] <= v_Cost[v] && v_Cost[v_b] <= v_Cost[v_a])
				{
					v_State[v_b] = STATE::Fixed;
					v_State[v_a] = STATE::Deleted;
					v_State[v] = STATE::Deleted;
				}
				else
				{
					int v_min;
					if (v_Cost[v] > v_Cost[v_a])
						v_min = v_a;
					else
						v_min = v;
					if (v_Degree[v_b] == 2) // v_b degree = 2
					{
						v_State[v] = STATE::Deleted;
						v_State[v_a] = STATE::Deleted;
						v_State[v_b] = STATE::Deleted;
						v_State[v_min] = STATE::Fixed;
					}
					else // v_b degree > 2
					{
						v_State[v_a] = STATE::Deleted;
						v_State[v] = STATE::Deleted;
						v_State[v_min] = v_b + 10;
						v_Cost[v_b] -= v_Cost[v_min];
					}
				}
			}
		}
	}
	int v_n, tms;
	memset(v_Num_Of_Dmnd, 0, (v_Num + 1) * sizeof(int));
	for (int v = 1; v <= v_Num; ++v)
	{
		if (v_State[v] == STATE::Fixed || v_State[v] > 10)
		{
			v_Num_Of_Dmnd[v]++;
			for (int i = 0; i < v_Degree[v]; ++i)
			{
				v_n = v_Adj[v][i];
				v_Num_Of_Dmnd[v_n]++;
			}
		}
		v_Adj[v][v_Degree[v]++] = v;
	}
	memcpy(v_Num_Of_Dmnd_Bak,v_Num_Of_Dmnd,sizeof(int)*(v_Num+1));
	memset(v_Dmn_size, 0, (v_Num + 1) * sizeof(int));
	memset(v_Dmnd_size, 0, (v_Num + 1) * sizeof(int));
	v_Dmn = v_Adj;
	for (int v = 1; v <= v_Num; ++v)
	{
		if (v_State[v] == STATE::Candidate)
		{
			for (int i = 0; i < v_Degree[v]; ++i) // degree = |N[v]|
			{
				v_n = v_Dmn[v][i];
				if (v_Num_Of_Dmnd[v_n] == 0)
				{
					tms = v_Dmn[v][v_Dmn_size[v]];
					v_Dmn[v][v_Dmn_size[v]] = v_n;
					v_Dmn[v][i] = tms;
					v_Dmn_size[v]++;

					v_Dmnd[v_n][v_Dmnd_size[v_n]++] = v;
				}
			}
			if (v_Dmn_size[v] == 0) // N[v] are all dmnd;
				v_State[v] = STATE::Deleted;
			v_Score[v] = v_Dmn_size[v];
			//v_Score_Real[v] = v_Dmn_size[v];
			v_Time_Stamp[v] = 0;
			cc[v] = 1;
		}
	}
    init_state_ubc_domcost_enable(v_State,v_Cost);
}

void eliminateRedundancy(int bms_size = 100) //each step, remove the vertex with the biggest cost
{
	int v_aim, v, i;
	while (Redundancy->size_ > 0)
	{
		if (Redundancy->size_ > bms_size)
		{
			v_aim = Redundancy->arr_[rand() % Redundancy->size_];
			for (i = 1; i < bms_size; ++i)
			{
				v = Redundancy->arr_[rand() % Redundancy->size_];
				if (v_Cost[v_aim] < v_Cost[v])
					v_aim = v;
			}
		}
		else
		{
			v_aim = Redundancy->arr_[0];
			for (i = 1; i < Redundancy->size_; ++i)
			{
				v = Redundancy->arr_[i];
				if (v_Cost[v_aim] < v_Cost[v])
					v_aim = v;
			}
		}
		removeVertex(v_aim);
	}
}


void updateBestSol()
{
	time_Sol = getLocalSearchTimeElapsed();
	sol_Best_Size = sol_Cur->size_;
	sol_Best_Cost = sol_Cur_Cost;
	for (int i = 0; i < sol_Cur->size_; ++i)
		sol_Best[i] = sol_Cur->arr_[i];

 #ifdef DEBUG
	cout << "Size: " << sol_Best_Size << " Cost: " << sol_Best_Cost << " Time: " << time_Sol << endl;
 #endif // DEBUG

}

void checkSol()
{
  int i, j;
  int v, v_n;
  int* is_dmnd = arr_Tmp;
  memset(is_dmnd, 0, (v_Num + 1) * sizeof(int));
  for(int i=0;i<USED(VEC_SOLUTION);i++){
    v=ITEM(VEC_SOLUTION,i);
    is_dmnd[v] = 1;
    for (j = 0; j < v_Degree[v]; ++j)
      {
	v_n = v_Adj[v][j];
	is_dmnd[v_n] = 1;
      }
  }
  for (i = 1; i <= v_Num; ++i)
    {
      if (is_dmnd[i] == 0)
	{
	  cout << " !!!!!checlSol: The solution is wrong! : some vertices have not been dominated" << endl;
	  return;
	}
    }
}


void checkBestSol()
{
	int i, j;
	int v, v_n;
	int* is_dmnd = arr_Tmp;
	memset(is_dmnd, 0, (v_Num + 1) * sizeof(int));
	USED(UNIT_STK)=0;
	for(v = 1; v <= v_Num; ++v){ //recover
	  clr_loved_status(v);
		if (v_State[v] == STATE::Fixed || v_State[v] > 10)
		{
			sol_Best[sol_Best_Size++] = v;
			sol_Best_Cost += v_Cost[v];
		}
	}

	for (i = 0; i < sol_Best_Size; ++i)
	{
		v = sol_Best[i];
		
		is_dmnd[v]++;
		for (j = 0; j < v_Degree[v]; ++j)
		{
			v_n = v_Adj[v][j];
			if(v_n!=v)
			  is_dmnd[v_n]++;
		}
	}
	for (i = 1; i <= v_Num; ++i)
	{
		if (is_dmnd[i] == 0)
		{
			cout << " ###The solution is wrong! : some vertices have not been dominated" << endl;
			return;
		}
		if(is_dmnd[i] == 1){
		  set_loved_status(i);
		  push_back(UNIT_STK,int,i);
		}
	}
	/*
	int* sol_origin = new int[v_Num + 1];
	long long cost_origin = 0;
	memset(sol_origin, 0, (v_Num + 1) * sizeof(int));
	for (i = 0; i < sol_Best_Size; ++i)
		sol_origin[sol_Best[i]] = 1;
	for (i = 1; i <= v_Num; ++i)
	{
		if (v_State[i] > 10)
		{
			v = v_State[i] - 10;
			if (sol_origin[v] == 1)
				sol_origin[i] = 0;
		}
		if (sol_origin[i] == 1)
			cost_origin += V_Cost_Origin[i];
	}
	if (cost_origin != sol_Best_Cost)
		cout << " ###The solution is wrong! : After recovering, Cost(i.e., weight) error" << endl;

	memset(is_dmnd, 0, (v_Num + 1) * sizeof(int));
	for (i = 1; i <= v_Num; ++i)
	{
		if (sol_origin[i] == 1)
		{
			for (j = 0; j < v_Degree[i]; ++j)
				is_dmnd[v_Adj[i][j]] = 1;
		}
	}
	for (i = 1; i <= v_Num; ++i)
	{
		if (is_dmnd[i] == 0)
		{
			cout << " ###The solution is wrong! : After recovering, some vertices have not been dominated" << endl;
		}
	}
	delete[] sol_origin;*/
}


void reset_config(){
  memcpy(v_Num_Of_Dmnd,v_Num_Of_Dmnd_Bak,(v_Num + 1) * sizeof(int));
  memset(v_Dmnd_v1,0,(v_Num + 1) * sizeof(int));
  memset(v_Dmnd_v2,0,(v_Num + 1) * sizeof(int));
  Undmnd->myClear();
  sol_Cur->myClear();
  Redundancy->myClear();
  for (int v = 1; v <= v_Num; ++v)
    {
      if (v_State[v] == STATE::Candidate)
	{
	  v_Score[v] = v_Dmn_size[v];
	  //v_Score_Real[v] = v_Dmn_size[v];
	  v_Time_Stamp[v] = 0;
	  cc[v] = 1;
	}
    }
}

void newConstructInit(){
   	int v, v_n;
	sol_Cur_Cost = 0;
	sol_Best_Cost = 0;
	sol_Best_Size = 0;
	fix_Num = 0;
	Step = 0;
	for (v = 1; v <= v_Num; ++v)
        {
	    if (v_State[v] == STATE::Deleted)
	      continue;
	    if (v_State[v] == STATE::Fixed || v_State[v] > 10)
	      {
		fix_Num++;
		//sol_Cur->push(v);
		//sol_Cur_Cost += v_Cost[v];
		continue;
	      }
	    if (v_Num_Of_Dmnd[v] == 0)
	      {
		v_Weight[v] = 1;
		Undmnd->push(v);
	      }
	}
	v_Score[0] = INT_MIN;
	//v_Score_Real[0] = INT_MIN;
	v_Cost[0] = 1;
	v_Time_Stamp[0] = LLONG_MAX;
	cc[0] = 1;
	//	printf("USED(VEC_PARTIA) %d\n",USED(VEC_PARTIAL));
	checkSol();
        for(int i=0;i<USED(VEC_SOLUTION);i++){
	  int v=ITEM(VEC_SOLUTION,i);
	  if (v_State[v] == STATE::Fixed || v_State[v] > 10)
	  {
	    continue;
	  }
	  newAddVertexInit(v);
	}
	assert(Undmnd->size_ == 0);
	eliminateRedundancy();
	updateBestSol();
}

void constructInit()
{
	int v, v_n;
	MAXHEAP* max_heap = new MAXHEAP(v_Num + 1);
	sol_Cur_Cost = 0;
	sol_Best_Cost = 0;
	sol_Best_Size = 0;
	fix_Num = 0;
	Step = 0;
	for (v = 1; v <= v_Num; ++v)
	{
		if (v_State[v] == STATE::Deleted)
			continue;
		if (v_State[v] == STATE::Fixed || v_State[v] > 10)
		{
			fix_Num++;
			//sol_Cur->push(v);
			//sol_Cur_Cost += v_Cost[v];
			continue;
		}
		if (v_Num_Of_Dmnd[v] == 0)
		{
			v_Weight[v] = 1;
			Undmnd->push(v);
		}
		max_heap->insert(v);
	}
	v_Score[0] = INT_MIN;
	//v_Score_Real[0] = INT_MIN;
	v_Cost[0] = 1;
	v_Time_Stamp[0] = LLONG_MAX;
	cc[0] = 1;

	while (Undmnd->size_ > 0) // add best per step
	{
		v = max_heap->removeRoot();
		addVertexInit(v, max_heap);
	}

	//while (Undmnd->size_ > 0) // add rand per step
	//{
	//	v = getAddVRand();
	//	v = getAddVBMS();
	//	//addVertex(v, nullptr);
	//	addVertexInit(v, nullptr);
	//	//cc[v] = 1;
	//}

	eliminateRedundancy();
	updateBestSol();

	//checkBestSol();
	delete max_heap;
}

int getRemoveVBMS(int bms_size = 100)
{
	int v, rn, v_aim = 0;
	int size_t = sol_Cur->size_;
	if (size_t == 0)
		return 0;
	if (size_t > bms_size)
	{
		v_aim = sol_Cur->arr_[rand() % size_t];
		for (int i = 1; i < bms_size; ++i)
		{
			v = sol_Cur->arr_[rand() % size_t];
			rn = compare(v_Score[v_aim], v_Cost[v_aim], v_Score[v], v_Cost[v]);
			if (rn < 0)
				v_aim = v;
			else if (rn == 0 && v_Time_Stamp[v_aim] > v_Time_Stamp[v])
				v_aim = v;
		}
	}
	else
	{
		v_aim = sol_Cur->arr_[0];
		for (int i = 1; i < sol_Cur->size_; ++i)
		{
			v = sol_Cur->arr_[i];
			rn = compare(v_Score[v_aim], v_Cost[v_aim], v_Score[v], v_Cost[v]);
			if (rn < 0)
				v_aim = v;
			else if (rn == 0 && v_Time_Stamp[v_aim] > v_Time_Stamp[v])
				v_aim = v;
		}
	}
	return v_aim;
}

int getAddVRand()
{
	int v_aim = 0, v_n, rn;
	int v = Undmnd->arr_[rand() % Undmnd->size_];
	for (int i = 0; i < v_Dmnd_size[v]; ++i)
	{
		v_n = v_Dmnd[v][i];
		if (cc[v_n] == 0)
		{
			if (Undmnd->size_ > 1 || sol_Cur_Cost + v_Cost[v_n] >= sol_Best_Cost)
			//if (Undmnd->size_ > v_Score_Real[v_n] || sol_Cur_Cost + v_Cost[v_n] >= sol_Best_Cost)
				continue;
		}
		rn = compare(v_Score[v_aim], v_Cost[v_aim], v_Score[v_n], v_Cost[v_n]);
		if (rn < 0)
		{
			v_aim = v_n;
		}
		else if (rn == 0)
		{
			if (cc[v_aim] < cc[v_n])
				v_aim = v_n;
			else if (cc[v_aim] == cc[v_n] && v_Time_Stamp[v_aim] > v_Time_Stamp[v_n])
			{
				v_aim = v_n;
			}
		}
	}
	if(v_aim == 0)
	//	v_aim = v;
		for (int i = 0; i < v_Dmnd_size[v]; ++i)
		{
			v_n = v_Dmnd[v][i];
			rn = compare(v_Score[v_aim], v_Cost[v_aim], v_Score[v_n], v_Cost[v_n]);
			if (rn < 0)
			{
				v_aim = v_n;
			}
			else if (rn == 0)
			{
				if (cc[v_aim] < cc[v_n])
					v_aim = v_n;
				else if (cc[v_aim] == cc[v_n] && v_Time_Stamp[v_aim] > v_Time_Stamp[v_n])
				{
					v_aim = v_n;
				}
			}
		}
	return v_aim;
}

void updateWeight()
{
	int v;
	for (int i = 0; i < Undmnd->size_; ++i)
	{
		v = Undmnd->arr_[i];
		v_Weight[v]++;
		for (int j = 0; j < v_Dmnd_size[v]; ++j)
			v_Score[v_Dmnd[v][j]]++;
	}
}


void removeN2(int v_aim)
{
	int v_n, v_n_n;
	removeVertex(v_aim);
	for (int i = 0; i < v_Dmn_size[v_aim]; ++i)
	{
		v_n = v_Dmn[v_aim][i];
		if (sol_Cur->pos_[v_n] != -1)
			removeVertex(v_n);
		for (int j = 0; j < v_Dmnd_size[v_n]; ++j)
		{
			v_n_n = v_Dmnd[v_n][j];
			if (sol_Cur->pos_[v_n_n] != -1)
				removeVertex(v_n_n);
		}
	}
}

int removeWorstTmp()
{
	if (sol_Tmp->size_ == 0)
		return 0;
	int v_aim = sol_Tmp->arr_[0], v;
	for (int i = 1; i < sol_Tmp->size_; ++i)
	{
		v = sol_Tmp->arr_[i];
		if (compare(v_Score[v_aim], v_Cost[v_aim], v_Score[v], v_Cost[v]) < 0)
			v_aim = v;
	}
	return v_aim;
}

int removeRandTmp()
{
	if (sol_Tmp->size_ == 0)
		return 0;
	return sol_Tmp->arr_[rand() % sol_Tmp->size_];
}

void localCC2V3()
{
	int v_add, v_remove, v;
	int step_unimprove = 0;
	while (step_unimprove < 50)//50
	{
		Step++; 
		step_unimprove++;
		while (Undmnd->size_ > 0)
		{
			v_add = getAddVRand();
			//if(v_add == 0)
			//	return;
			addVertex(v_add);
			sol_Tmp->push(v_add);
			updateWeight();
		}
		while (Redundancy->size_ > 0)
		{
			v = Redundancy->arr_[rand() % Redundancy->size_];
			removeVertex(v);
			if (sol_Tmp->pos_[v] != -1)
				sol_Tmp->pop(v);
		}
		if (sol_Cur_Cost < sol_Best_Cost)
		{
			updateBestSol();
			step_unimprove = 0;
		}
		v_remove = removeWorstTmp();
		if (v_remove > 0)
		{
			removeVertex(v_remove);
			sol_Tmp->pop(v_remove);
		}
		else
			return;
		v_remove = removeRandTmp();
		if (v_remove > 0)
		{
			removeVertex(v_remove);
			sol_Tmp->pop(v_remove);
		}
		else
			return;
	}
}

void interfere()
{
	int v_aim;
	int size_tmp = rand() % 5 + 1;//5
	for (int i = 0; i < size_tmp; ++i)
	{
		if (sol_Cur->size_ > 0)
			v_aim = sol_Cur->arr_[rand() % sol_Cur->size_];
		else
			break;
		removeN2(v_aim);
	}
	sol_Tmp->myClear();
	localCC2V3();
}


void localSearch(double timeout)
{
	int v_add, v_remove;
	int step_try = 10;
	int step_unimprove = 0;
	Step = 1;

	if (Pattern == 1)
		gap = sol_Cur_Cost / sol_Cur->size_;
	else if (Pattern == 0)
	{
		v_Cost_Max_In_Cand = sol_Cur->arr_[0];
		for (int i = 1; i < sol_Cur->size_; ++i)
			if (v_Cost[sol_Cur->arr_[i]] > v_Cost[v_Cost_Max_In_Cand])
				v_Cost_Max_In_Cand = sol_Cur->arr_[i];
		gap = v_Cost[v_Cost_Max_In_Cand];
	}

	//int count_tmp = 0;

	while (true)
	{
		//eliminateRedundancy(); // TO DO location
		Step++;
		step_unimprove++;
		//	if (Step % step_try == 0)
		//{
		       if (getLocalSearchTimeElapsed() > timeout)
				return;
		       //}

		if (step_unimprove >= 20000)//20000 Location
		{

		  interfere();
		  step_unimprove = 0;
		  //	return ;
			//cout << "interfere" << ++count_tmp << " " << getTimeElapsed() << endl;
		}

		if (Undmnd->size_ == 0)
		{
			eliminateRedundancy(); // TO DO location
			if (sol_Cur_Cost < sol_Best_Cost)
			{
				updateBestSol();
				step_unimprove = 0;
			}
			v_remove = getRemoveVBMS();
			removeVertex(v_remove);
			//continue;
		}

		v_remove = getRemoveVBMS();
		if (v_remove > 0)
			removeVertex(v_remove);
		while (sol_Cur_Cost + gap >= sol_Best_Cost)
		{
			v_remove = getRemoveVBMS();
			if (v_remove == 0)
				break;
			removeVertex(v_remove);
		}

		while (Undmnd->size_ > 0)
		{
			v_add = getAddVRand();
			if (sol_Cur_Cost + v_Cost[v_add] + gap <= sol_Best_Cost) // TO DO check (equal sign)
			{
				addVertex(v_add);
			}
			else
			{
				v_remove = getRemoveVBMS();
				if (v_Score[v_remove] == 0)
				{
					removeVertex(v_remove);
					continue;
				}
				if (v_remove > 0 && compare(-v_Score[v_remove], v_Cost[v_remove], v_Score[v_add], v_Cost[v_add]) < 0)
				{
					removeVertex(v_remove);
					addVertex(v_add);
				}
				else
				{
					if (rand() / (RAND_MAX + 1.0) < 1.0 / (double)Undmnd->size_)
					//if (rand() / (RAND_MAX + 1.0) < v_Score_Real[v_add] / (double)Undmnd->size_)
					{
						addVertex(v_add);
					}
					else
					{
						break;
					}
				}
			}
		}
		updateWeight();
	}
}

