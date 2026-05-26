#include "cc42.h"

int bms_thre = 1;
int bms;
//int each_iter=0;
long long each_iter;
long current_sol;
long current_sol_bak;
int remove_num1, remove_num2;


void buger()
{
   printf(" *\n");
}

void init(){
  best_value=LONG_MAX; //取最大值
  best_best_value=LONG_MAX; //取最大值
  cs_size = 0;
  locked_num = 0;
  tabu_list.clear();
   current_sol = 0;
   t_length = 0;
   //memset(t_index, -1, sizeof(t_index));
   for(int i = 0; i < vertex_num; i++)
   {
       t_index[i] = -1;
   }

}

void init_reduce()
{
    int i,j,v,kn;
    int a,b,c,sum;
    int v_neighbor, neighbor_num;

    memset(reduce, 0, vertex_num * sizeof(int));
    for(i = 0; i < vertex_num; i++)
    {
        if(vertex_neightbourNum[i] == 1)
        {
            v_neighbor = vertex[i][0];
            if(cs[i].cost > cs[v_neighbor].cost)
            {
                reduce[i] = 1;
                cs[v_neighbor].locked = 1;
            }
        }
        else if(vertex_neightbourNum[i] == 2)
        {
            if(vertex_neightbourNum[vertex[i][0]] == 2)
            {
                a = vertex[i][0];
                b = vertex[i][1];
            }
            else if(vertex_neightbourNum[vertex[i][1]] == 2)
            {
                a = vertex[i][1];
                b = vertex[i][0];
            }
            else
                continue;
            if(vertex[a][0] == i)
                c = vertex[a][1];
            else
                c = vertex[a][0];
            if(b == c)
            {

                if(cs[i].cost > cs[b].cost && cs[a].cost > cs[b].cost)
                {
                    reduce[i] = 1;
                    reduce[a] = 1;
                    cs[b].locked = 1;
                }
            }
        }
        else if(vertex_neightbourNum[i] == 0)
        {
             cs[i].locked = 1;
        }

        else
        {
            neighbor_num = vertex_neightbourNum[i];
            sum = 0;
            for(j = 0; j < neighbor_num; j++){
	      // assert(vertex[i][j]>=0 && vertex[i][j]<vertex_num);
	      //printf("i %d j  %d  neighbor_num %d vertex[i][j] %d\n",i,j,neighbor_num,vertex[i][j]);
                if(vertex_neightbourNum[vertex[i][j]] == 1)
                    sum += cs[vertex[i][j]].cost;
	    }

            if(sum > cs[i].cost)
            {
                for(j = 0; j < neighbor_num; j++)
                    if(vertex_neightbourNum[vertex[i][j]] == 1)
                    {
                        reduce[vertex[i][j]] = 1;
                    }
                cs[i].locked = 1;
            }
        }
    }
    int kkk,k;
    int lenn;
    remain_num = 0;
    for(i = 0; i < vertex_num; i++)
    {
		
        if(reduce[i])
        {

            neighbor_num = vertex_neightbourNum[i];
            for(j = 0; j < neighbor_num; j++)
            {
                v_neighbor = vertex[i][j];
                lenn = vertex_neightbourNum[v_neighbor];
                for(k = 0; k < lenn; k++)
                    if(vertex[v_neighbor][k] == i)
                        break;
                vertex_neightbourNum[v_neighbor]--;
                kkk = vertex[v_neighbor][vertex_neightbourNum[v_neighbor]];
                vertex[v_neighbor][vertex_neightbourNum[v_neighbor]] = vertex[v_neighbor][k];
                vertex[v_neighbor][k] = kkk;
            }
        }
        else
        {

            //uncover_vertex[remain_num] = i;
            //uncover_vertex_index[i] = remain_num;
            remain_vertex[remain_num++] = i;
        }
	if(reduce[i])
	  uncover_vertex_index[i]=2;
	else if(cs[i].locked)
	   uncover_vertex_index[i]=1;
	else
	   uncover_vertex_index[i]=0;
	
    }
    init_state_ubc_domcost_enable(uncover_vertex_index);
    //uncover_num = remain_num;
    //printf("%d %d ", vertex_num, remain_num);

}

inline int compare(int s1, int c1, int s2, int c2){
  if(c1==c2) {
    if(s1>s2) return 1;
    else if(s1==s2) return 0;
    else return -1;
  }
  long long t1=s1, t2=s2;
  t1=t1*c2;
  t2=t2*c1;
  if(t1>t2) return 1;
  else if(t1==t2) return 0;
  else return -1;
}
/*
int check(){ // check if the solution is a correct cover
  int i,j,k,v;
  for(v=0;v<remainnum;v++)
  {
      j = remain_vertex[v];
      reduce[j] = 0;
  }

  for(v=0;v<remain_num;v++){
      j = remain_vertex[v];
      if(best_sol[j]==0 && cs[j].locked == 1)
        return 0;
     if(best_sol[j]==0) continue;
     reduce[j]=1;
     for(k=0;k<vertex_neightbourNum[j];k++){
       reduce[vertex[j][k]]=1;
     }
  }
  for(v=0;v<remain_num;v++){
      i = remain_vertex[v];
     if(!reduce[i]) return 0;
  }
  return 1;
}*/

int check(){ // check if the solution is a correct cover
  int i,j,k,v;

  for(v=0;v<vertex_num;v++)
    {
      reduce[v] = 0;
    }
  for(v=0;v<vertex_num;v++){
    j = v;
    if (best_sol[j] == 0 && cs[j].locked == 1)
      {
	return 0;
      }
    if(best_sol[j]==0) continue;
    reduce[j]++;
    for(k=0;k<vertex_neightbourNum1[j];k++){
      reduce[vertex[j][k]]++;
    }
  }
  for(v=0;v<vertex_num;v++){
    i = v;
    if(!reduce[i]) return 0;
  }
  return 1;
}


void init_after_reduction(){
  int cnt, kn;
  int i,j,k,l,jj,v;
  int sr, ct;
  for(v = 0; v < remain_num; v++)
  {
      i = remain_vertex[v];
      if(cs[i].locked)
      {
          cs[i].is_in_c = 1;
          cs[i].num_in_c++;
          current_sol += cs[i].cost;
          kn = vertex_neightbourNum[i];
          for(j = 0; j < kn; j++)
            cs[vertex[i][j]].num_in_c++;

      }
  }
  uncover_num = 0;
   for(v = 0; v < remain_num; v++)
   {
        i = remain_vertex[v];
        if(cs[i].locked)
            continue;
        kn = vertex_neightbourNum[i];
        for(k = 0; k <kn; k++)
        {
            j = vertex[i][k];
            if(cs[j].num_in_c == 0)
                cs[i].score += 1;
        }
        if(cs[i].num_in_c == 0)
        {
            cs[i].score += 1;
            uncover_vertex[uncover_num] = i;
            uncover_vertex_index[i] = uncover_num;
            uncover_num++;
        }
   }
   //save cs;
   uncover_num_bak= uncover_num;
   current_sol_bak=current_sol;
   memcpy(cs_bak,cs,vertex_num*sizeof(Vertex_information));
   memcpy(uncover_vertex_bak, uncover_vertex,vertex_num*sizeof(int));
   memcpy(uncover_vertex_index_bak, uncover_vertex_index,vertex_num*sizeof(int));
}

void reset_config(){
  bms = 100;
  best_value=LONG_MAX;
  cs_size = 0;
  locked_num = 0;
  t_length = 0;
  tabu_list.clear();
  for(int i = 0; i < vertex_num; i++){
    t_index[i] = -1;
    vertex_weight[i]=1;
  }

  current_sol=current_sol_bak;
  uncover_num =uncover_num_bak;
  memcpy(cs,cs_bak,vertex_num*sizeof(Vertex_information));
  memcpy(uncover_vertex, uncover_vertex_bak,vertex_num*sizeof(int));
  memcpy(uncover_vertex_index, uncover_vertex_index_bak,vertex_num*sizeof(int));
}


void init_best(){
  int cnt, kn;
  int i,j,k,l,jj,v;
  int sr, ct;
  for(v = 0; v < remain_num; v++)
  {
      i = remain_vertex[v];
      if(cs[i].locked)
      {
          cs[i].is_in_c = 1;
          cs[i].num_in_c++;
          current_sol += cs[i].cost;
          kn = vertex_neightbourNum[i];
          for(j = 0; j < kn; j++)
            cs[vertex[i][j]].num_in_c++;

      }
  }
    uncover_num = 0;
   for(v = 0; v < remain_num; v++)
   {
        i = remain_vertex[v];
        if(cs[i].locked)
            continue;
        kn = vertex_neightbourNum[i];
        for(k = 0; k <kn; k++)
        {
            j = vertex[i][k];
            if(cs[j].num_in_c == 0)
                cs[i].score += 1;
        }
        if(cs[i].num_in_c == 0)
        {
            cs[i].score += 1;
            uncover_vertex[uncover_num] = i;
            uncover_vertex_index[i] = uncover_num;
            uncover_num++;
        }

   }
int sst = 0;
  int uncover_v;
  while(uncover_num>0){
/*
    if(sst % 2000 == 0)
    {
             times(&finish);
            double finish_time = double(finish.tms_utime - start.tms_utime + finish.tms_stime - start.tms_stime)/sysconf(_SC_CLK_TCK);
            finish_time = round(finish_time * 100)/100.0;
        printf("%d %d %f", sst , uncover_num, finish_time);
        buger();
    }
    sst++;*/
    uncover_v = uncover_vertex[rand()%uncover_num];

    sr = cs[uncover_v].score;
    ct = cs[uncover_v].cost;
    best_array[0] = uncover_v;
    cnt = 1;
    kn = vertex_neightbourNum[uncover_v];
    for(v=0;v<kn;v++){
      j = vertex[uncover_v][v];
      if(cs[j].is_in_c) continue;
      //if(cs[j].num_in_c > 0) continue;
      k=compare(sr,ct,cs[j].score, cs[j].cost);
      if(sr==INT_MIN||k<0){
	sr=cs[j].score;
	ct=cs[j].cost;
	best_array[0]=j;
	cnt=1;
      } else if(k==0){
	best_array[cnt++]=j;
      }
    }
    if(cnt>0){
      l=rand()%cnt;
      add(best_array[l], 1, 0);
    }
  }
    update_best_sol();
    if(check()==0){
        printf("initial wrong\n");exit(0);
  }
  printf("%ld	%.2f	", best_value, real_time);
}


void init_solution(){
  int cnt, kn;
  int i,j,k,l,jj,v;
  int sr, ct;
  
  /* for(v = 0; v < remain_num; v++)
  {
      i = remain_vertex[v];
      if(cs[i].locked)
      {
          cs[i].is_in_c = 1;
          cs[i].num_in_c++;
          current_sol += cs[i].cost;
          kn = vertex_neightbourNum[i];
          for(j = 0; j < kn; j++)
            cs[vertex[i][j]].num_in_c++;

      }
  }
    uncover_num = 0;
   for(v = 0; v < remain_num; v++)
   {
        i = remain_vertex[v];
        if(cs[i].locked)
            continue;
        kn = vertex_neightbourNum[i];
        for(k = 0; k <kn; k++)
        {
            j = vertex[i][k];
            if(cs[j].num_in_c == 0)
                cs[i].score += 1;
        }
        if(cs[i].num_in_c == 0)
        {
            cs[i].score += 1;
            uncover_vertex[uncover_num] = i;
            uncover_vertex_index[i] = uncover_num;
            uncover_num++;
        }

	}
 */
  
  //printf("%d  ", vertex_num - uncover_num);

  int sst = 0;
  int uncover_v;


  for(int i=0;i<USED(VEC_SOLUTION);i++){
    int v=ITEM(VEC_SOLUTION,i)-1;
    if(cs[v].locked){
	continue;
     }
     add(v, 1, 0);
  }
  assert(uncover_num==0);
  /* 
  while(uncover_num>0){

//    if(sst % 2000 == 0)
//    {
//             times(&finish);
//            double finish_time = double(finish.tms_utime - start.tms_utime + finish.tms_stime - start.tms_stime)/sysconf(_SC_CLK_TCK);
//            finish_time = round(finish_time * 100)/100.0;
//        printf("%d %d %f", sst , uncover_num, finish_time);
//        buger();
//    }
//    sst++;
    uncover_v = uncover_vertex[rand()%uncover_num];

    sr = cs[uncover_v].score;
    ct = cs[uncover_v].cost;
    best_array[0] = uncover_v;
    cnt = 1;
    kn = vertex_neightbourNum[uncover_v];
    for(v=0;v<kn;v++){
      j = vertex[uncover_v][v];
      if(cs[j].is_in_c) continue;
      //if(cs[j].num_in_c > 0) continue;
      k=compare(sr,ct,cs[j].score, cs[j].cost);
      if(sr==INT_MIN||k<0){
	sr=cs[j].score;
	ct=cs[j].cost;
	best_array[0]=j;
	cnt=1;
      } else if(k==0){
	best_array[cnt++]=j;
      }
    }
    if(cnt>0){
      l=rand()%cnt;
      add(best_array[l], 1, 0);
    }
  }
*/
  
    update_best_sol();
    if(check()==0){
        printf("initial wrong\n");exit(0);
  }
    // printf("%ld	%.2f	", best_value, real_time);
}


void add(int c, int locked_add, int init_add){
  int i,j,k,cnt,s, ii, jj, ix,h, l;
  int uk,ck;
  cs[c].is_in_c=1;
  current_sol += cs[c].cost;
  if(locked_add == 1)
  {
        cs_vertex[cs_size] = c;
        cs_vertex_index[c] = cs_size;
        cs_size++;
  }

  cs[c].score=-cs[c].score;
  if(cs[c].score == 0 && t_index[c] == -1 && cs[c].locked == 0)
  {
      t[t_length] = c;
      t_index[c] = t_length;
      t_length++;
  }

  if( cs[c].num_in_c==0)
  {
      uncover_num--;
      if(init_add == 0)
      {
            uk = uncover_vertex_index[c];
            ck = uncover_vertex[uncover_num];
            uncover_vertex[uk] = ck;
            uncover_vertex_index[ck] = uk;
      }
  }


  for(h=0;h<vertex_neightbourNum[c]; h++){//C集合中每一个变量h   处理未覆盖集合
    i=vertex[c][h];

    if(cs[i].num_in_c==0)
    {
      uncover_num--;
      if(init_add == 0)
      {
            uk = uncover_vertex_index[i];
            ck = uncover_vertex[uncover_num];
            uncover_vertex[uk] = ck;
            uncover_vertex_index[ck] = uk;
      }
   }

    cs[i].num_in_c++;/////////////////////
    cnt=0;
    if( cs[c].num_in_c==0){
      cs[i].score-=vertex_weight[c];
    }    else if( cs[c].num_in_c==1&& cs[i].is_in_c==1){
      cs[i].score+=vertex_weight[c];
    }


    if(cs[i].is_in_c && init_add == 0)
    {
         if(cs[i].num_in_c == 2)
            cs[i].score += vertex_weight[i];
         if(cs[i].score == 0 && t_index[i] == -1 && cs[i].locked == 0)
         {
             t[t_length] = i;
             t_index[i] = t_length;
             t_length++;
         }
         else if(t_index[i] != -1 && cs[i].score != 0)
         {
             t_length--;
             uk = t_index[i];
             ck = t[t_length];
             t[uk] = ck;
             t_index[ck] = uk;
             t_index[i] = -1;
         }
         continue;
    }


     cs[i].config = 1;
     //if(init_add == 0)
        //cs[i].config = 2;
    for(l=0;l<vertex_neightbourNum[i];l++){//因为这个变量，变成这个集合的邻居集合
      j=vertex[i][l];

      if(j==c) continue;
      if(cs[j].is_in_c){
	s=j;
	cnt++;
      }
        //if(rand()%100 < 50)
        //if(init_add == 1)
            cs[j].config = 2;
    }
    if(cs[i].is_in_c){
      s=i;
      cnt++;
    }

    if(cnt==0){ // c is the first one covering this row in C
        cs[i].score-=vertex_weight[i];////////////////
        for(l=0; l<vertex_neightbourNum[i]; l++){
            j=vertex[i][l];
            if(j==c)
                continue;
            cs[j].score-=vertex_weight[i];//候选解中不覆盖这个变量，所以当覆盖之后，所以以前覆盖这个变量的集合score取值必须减去这个变量
            if(cs[j].score == 0 && cs[j].is_in_c == 1 && t_index[j] == -1 && cs[j].locked == 0)
            {
                t[t_length] = j;
                t_index[j] = t_length;
                t_length++;
            }
            else if(t_index[j] != -1 && cs[j].score != 0)
            {
                t_length--;
                uk = t_index[j];
                ck = t[t_length];
                t[uk] = ck;
                t_index[ck] = uk;
                t_index[j] = -1;
            }
        }
    } else if(cnt==1){// c is second one covering this row in C
        cs[s].score+=vertex_weight[i];//候选解中覆盖这个变量一次，所以加入这个集合以后，所以以前覆盖这个变量的集合score取值必须加上这个变量
        if(cs[s].score == 0 && cs[s].is_in_c == 1 && t_index[s] == -1 && cs[s].locked == 0)
        {
            t[t_length] = s;
            t_index[s] = t_length;
            t_length++;
        }
        else if(t_index[s] != -1 && cs[s].score != 0)
        {
            t_length--;
            uk = t_index[s];
            ck = t[t_length];
            t[uk] = ck;
            t_index[ck] = uk;
            t_index[s] = -1;
        }
    }

    if(cs[i].score == 0 && cs[i].is_in_c == 1 && t_index[i] == -1 && cs[i].locked == 0)
    {
        t[t_length] = i;
        t_index[i] = t_length;
        t_length++;
    }
    else if(t_index[i] != -1 && cs[i].score != 0)
    {
        t_length--;
        uk = t_index[i];
        ck = t[t_length];
        t[uk] = ck;
        t_index[ck] = uk;
        t_index[i] = -1;
    }
  }
    cs[c].num_in_c++;
}

void remove(int c, int init_remove){
  int uk, ck;
  cs[c].is_in_c=0;
  current_sol -= cs[c].cost;
  cs_size--;
  int kn = cs_vertex_index[c];
  int bn = cs_vertex[cs_size];
  cs_vertex[kn] = bn;
  cs_vertex_index[bn] = kn;

  cs[c].score=-cs[c].score;
  if(cs[c].score == 0 && t_index[c] != -1)
  {
      t_length--;
      uk = t_index[c];
      ck = t[t_length];
      t[uk] = ck;
      t_index[ck] = uk;
      t_index[c] = -1;
  }
  //if(init_remove == 1)
        cs[c].config=0;

  if( cs[c].num_in_c==1)
  {
      //uncover_vertex[uncover_num] = c;//////////////////////////
     // uncover_vertex_index[c] = uncover_num;
      uncover_num++;
  }

  int i,j,k,cnt,s,h,l;
  for(h=0; h<vertex_neightbourNum[c]; h++){
    i=vertex[c][h];
    if(cs[i].num_in_c==1)
    {
      //uncover_vertex[uncover_num] = i;
      //uncover_vertex_index[c] = uncover_num;
      //uncover_vertex_index[i] = uncover_num;
      uncover_num++;
    }
    cs[i].num_in_c--;
    cnt=0;
     if( cs[c].num_in_c==2&& cs[i].is_in_c==1){
      cs[i].score-=vertex_weight[c];
    }    else if( cs[c].num_in_c==1){
      cs[i].score+=vertex_weight[c];
    }


    if(cs[i].is_in_c && init_remove == 0)
    {
        if(cs[i].num_in_c == 1)
            cs[i].score -= vertex_weight[i];
        if(cs[i].score == 0 && t_index[i] == -1 && cs[i].locked == 0)
        {
            t[t_length] = i;
            t_index[i] = t_length;
            t_length++;
        }
        else if(t_index[i] != -1 && cs[i].score != 0)
        {
            t_length--;
            uk = t_index[i];
            ck = t[t_length];
            t[uk] = ck;
            t_index[ck] = uk;
            t_index[i] = -1;
        }
        continue;
    }
    //if(init_remove == 1)
     cs[i].config = 2;
    for(l=0;l<vertex_neightbourNum[i];l++){
      j=vertex[i][l];
      if(j==c) continue;
      if(cs[j].is_in_c){
	cnt++;
	s=j;
      }
        //if(rand()%100 < 50)
        //if(init_remove == 1)
         cs[j].config=2;
    }
    if(cs[i].is_in_c){
	s=i;
	cnt++;
      }
    if(cnt==0){
        cs[i].score+=vertex_weight[i];////////////////
        for(l=0;l<vertex_neightbourNum[i];l++){
            j=vertex[i][l];
            if(j==c)
                continue;
            cs[j].score+=vertex_weight[i];
            if(cs[j].score == 0 && cs[j].is_in_c == 1 && t_index[j] == -1 && cs[j].locked == 0)
            {
                t[t_length] = j;
                t_index[j] = t_length;
                t_length++;
            }
            else if(t_index[j] != -1 && cs[j].score != 0)
            {
                t_length--;
                uk = t_index[j];
                ck = t[t_length];
                t[uk] = ck;
                t_index[ck] = uk;
                t_index[j] = -1;
            }
        }
    } else if(cnt==1){
        cs[s].score-=vertex_weight[i];
        if(cs[s].score == 0 && cs[s].is_in_c == 1 && t_index[s] == -1 && cs[s].locked == 0)
        {
            t[t_length] = s;
            t_index[s] = t_length;
            t_length++;
        }
        else if(t_index[s] != -1 && cs[s].score != 0)
        {
            t_length--;
            uk = t_index[s];
            ck = t[t_length];
            t[uk] = ck;
            t_index[ck] = uk;
            t_index[s] = -1;
        }
    }
    if(cs[i].score == 0 && cs[i].is_in_c == 1 && t_index[i] == -1 && cs[i].locked == 0)
    {
        t[t_length] = i;
        t_index[i] = t_length;
        t_length++;
    }
    else if(t_index[i] != -1 && cs[i].score != 0)
    {
        t_length--;
        uk = t_index[i];
        ck = t[t_length];
        t[uk] = ck;
        t_index[ck] = uk;
        t_index[i] = -1;
    }
  }
    cs[c].num_in_c--;

}

int in_tabu(int i){
  return tabu_list.find(i)!=tabu_list.end();
}
int state=0;

int find_best_in_c_simp(int allowTabu){
  int i, maxc,j,k,v;

  int sr=INT_MIN, ct=1;
  int kn = cs_size;
  state = 0;
  for(v=0;v<kn;v++){
        i = v;
        i = cs_vertex[i];
        if(allowTabu&&in_tabu(i))
            continue;
        state = 1;
        k=compare(sr,ct, cs[i].score, cs[i].cost);
        if(sr==INT_MIN||k<0){
            sr=cs[i].score;
            ct=cs[i].cost;
            //maxc=i;
            maxc=i;
        } else if(k==0){
        if(cs[maxc].time_stamp>cs[i].time_stamp){
            //maxc=i;
            maxc=i;
        }
        }
  }
  return maxc;
}

int find_best_in_c(int allowTabu){
  int i, maxc,j,k,v;
  int sr=INT_MIN, ct=1;
  int temp_int;
  int kn,flag;
  state=0;
  double r_n = rand()/(RAND_MAX+1.0);
  //double p = 1.0 / (double)best_sol_found;
  double p = exp(-each_iter);
  if(r_n < p)
  {
        //kn = cs_size;
        //bms = INT_MAX;
        kn = 1024;
  }
  else
  {
        /*bms = 100;
        temp_int = bms_thre % cs_size;
        if(bms < temp_int)
            bms = temp_int;
        kn = cs_size;
        if(kn > bms)
                kn = bms;*/
        kn = cs_size / 10;
        if(kn < 50) kn = 50;
        kn += rand() % (kn / 5 + 1);
  }
        if(kn > cs_size)
            kn = cs_size;
        for(v=0;v<kn;v++){
            if(cs_size == kn)
                i = v;
            else
                i = rand()%cs_size;
            i = cs_vertex[i];
            if(allowTabu&&in_tabu(i)) continue;
            state=1;
            k=compare(sr,ct, cs[i].score, cs[i].cost);
            if(sr==INT_MIN||k<0){
                sr=cs[i].score;
                ct=cs[i].cost;
                maxc=i;
            } else if(k==0){
                    if(cs[maxc].time_stamp>cs[i].time_stamp){
                        maxc=i;
                    }
            }
        }
  return maxc;
}

void uncov_r_weight_inc(){
  int i,j,h,v,nn;
  for(v = 0; v < uncover_length; v++)
  {
      i = uncover_vertex[v];
      if(cs[i].num_in_c == 0)
      {
          vertex_weight[i] += 1;
          cs[i].score += 1;
          nn = vertex_neightbourNum[i];
          for(h = 0; h < nn; h++)
          {
              j = vertex[i][h];
              cs[j].score += 1;
          }
      }
  }
}

void localsearch(double _timeout){
  step=1;
  int i,j,k,h,l,v,c;
  int best_in_c;
  int maxc;
  int flag = 0;
  int rand_n;
  int init_remove = 0;
  times(&start);
  real_time=0;
  start_time = start.tms_utime + start.tms_stime;
for(v = 0; v < vertex_num; v++)
    uncover_vertex_index[v] = -1;

//while(step<=maxStep){
while(true){
  i = -1;
  while(uncover_num == 0)
  {

      if(t_length > 0)
      {

          rand_n = rand()%t_length;
          i = t[rand_n];
      }
      else
      {
          update_best_sol();///////////////////
          //i = find_best_in_c_simp(1);
          //if(state == 0)
            i = find_best_in_c_simp(0);
          init_remove = 1;
      }
      remove(i, init_remove);
      if(USE_ADVANCED && each_iter > 200 && t_length > 0 && uncover_num == 0){
        int extra = 1 + rand() % 3;
        for(int ek = 0; ek < extra && t_length > 0 && uncover_num == 0; ek++){
          rand_n = rand() % t_length;
          int ei = t[rand_n];
          remove(ei, init_remove);
        }
      }
  }

     times(&finish);
     double finish_time = double(finish.tms_utime - start.tms_utime + finish.tms_stime - start.tms_stime)/sysconf(_SC_CLK_TCK);
     finish_time = round(finish_time * 100)/100.0;
     if(finish_time> _timeout) break;

  init_remove = 1;
  remove_num1 = i;
 // cout << "r " << i;
  //memset(uncover_vertex_index, -1, sizeof(uncover_vertex_index));
  uncover_length = 0;

  uncover_vertex[uncover_length] = remove_num1;
  uncover_vertex_index[remove_num1] = uncover_length;
  uncover_length++;

  h = vertex_neightbourNum[remove_num1];
  for(v = 0; v < h;v++)
  {
      i = vertex[remove_num1][v];
      if(cs[i].is_in_c == 1)
        continue;
      if(cs[i].is_in_c == 0 && uncover_vertex_index[i] == -1)
      {
          uncover_vertex[uncover_length] = i;
          uncover_vertex_index[i] = uncover_length;
          uncover_length++;
      }
      k = vertex_neightbourNum[i];
      for(j = 0; j < k; j++)
      {
          c = vertex[i][j];
          if(c == remove_num1)
            continue;
          if(cs[c].is_in_c == 0 && uncover_vertex_index[c] == -1)
          {
              uncover_vertex[uncover_length] = c;
              uncover_vertex_index[c] = uncover_length;
              uncover_length++;
          }
      }
  }

    best_in_c=find_best_in_c(1);
    if(state==0)best_in_c=find_best_in_c(0);
    tabu_list.clear();
    remove(best_in_c, init_remove);
    cs[best_in_c].time_stamp=step;
    //cout << " "<<best_in_c;
    //buger();
    if(uncover_vertex_index[best_in_c] == -1)
    {
        uncover_vertex[uncover_length] = best_in_c;
        uncover_vertex_index[best_in_c] = uncover_length;
        uncover_length++;
    }

    h = vertex_neightbourNum[best_in_c];
    for(v = 0; v < h; v++)
    {
        i = vertex[best_in_c][v];
        if(cs[i].is_in_c == 1)
            continue;
        if(cs[i].is_in_c == 0 && uncover_vertex_index[i] == -1)
        {
            uncover_vertex[uncover_length] = i;
            uncover_vertex_index[i] = uncover_length;
            uncover_length++;
        }
        k = vertex_neightbourNum[i];
        for(j = 0; j < k; j++)
        {
            c = vertex[i][j];
            if(c == best_in_c)
                continue;
            if(cs[c].is_in_c == 0 && uncover_vertex_index[c] == -1)
            {
                uncover_vertex[uncover_length] = c;
                uncover_vertex_index[c] = uncover_length;
                uncover_length++;
            }
        }
    }
    //cout << "a";
    while(uncover_num>0){

        int sr=INT_MIN, ct;
        maxc=-1;

        for(v = 0; v < uncover_length; v++)
        {
            j = uncover_vertex[v];
            if(cs[j].config == 0 || cs[j].is_in_c == 1)
                continue;
           	k=compare(sr,ct, cs[j].score, cs[j].cost);
            if(sr==INT_MIN||k<0){
                sr=cs[j].score;
                ct=cs[j].cost;
                maxc=j;
            }
            else if(k == 0){
              if(cs[maxc].config < cs[j].config)
                maxc = j;
              else if(cs[maxc].config == cs[j].config){//平分，优先选那个在 AQ 中历史表现更好的点。
                if(AQ_ENABLED && AQ_ACTIVE && AQ_TOUCH_UB && AQ[j+1] > AQ[maxc+1])
                  maxc = j;
                else if(cs[j].time_stamp < cs[maxc].time_stamp)
                  maxc = j;
              }
            }
        }
            assert(maxc != -1);
            add(maxc, 1, 1);
            tabu_list.insert(maxc);
            cs[maxc].time_stamp = step;
            uncov_r_weight_inc();
           //cout <<" " <<maxc ;
    }
    //buger();
    for(v = 0; v < uncover_length; v++)
        uncover_vertex_index[uncover_vertex[v]] = -1;

    //update_best_sol();
    step++;
	each_iter++;
	bms_thre = bms_thre*2;
	if(bms_thre >cs_size)bms_thre-=cs_size;
    //if(step>=total_step) break;
  }
    printf("%11ld %11ld  %10.4lf  %10.4lf\n", best_value,best_best_value,real_time,get_utime()-read_time);
}


void update_best_sol(){
  //当 uncover_num == 0（所有节点都被覆盖了）而且 t_length == 0（没有"可以安全移除而不破坏覆盖"的候选节点了），说明当前解已经是一个局部最优解——不能再删任何一个点了。这时候就调用 update_best_sol() 记录这个解。
  int i,j,v;
  if(current_sol < best_value){
	each_iter=0;
    best_value = current_sol;
    if(best_value<best_best_value){
      best_best_value=best_value;
      //让上界解质量直接影响后续下界构造
      static int *ub_sol_verts = NULL;
      static int ub_sol_cap = 0;
      if(ub_sol_cap < remain_num){
        ub_sol_verts = (int*)realloc(ub_sol_verts, remain_num * sizeof(int));
        ub_sol_cap = remain_num;
      }
      int sol_cnt = 0;
      for(v=0;v<remain_num;v++){
        j = remain_vertex[v];
        if(cs[j].is_in_c)
          ub_sol_verts[sol_cnt++] = j + 1;
      }
      aq_ub_feedback(ub_sol_verts, sol_cnt, best_best_value);
    }
    for(v=0;v<remain_num;v++){
        j = remain_vertex[v];
        best_sol[j]=0;
        if(cs[j].is_in_c){
            best_sol[j]=1;
      }
    }

    times(&finish);
    real_time = double(finish.tms_utime - start.tms_utime + finish.tms_stime - start.tms_stime)/sysconf(_SC_CLK_TCK);
    real_time = round(real_time * 100)/100.0;
  }
}

int main(int argc, char *argv[]){
  int i=0;
  double timeout=1.0;
  double gap_thd=0.001;
  if(argc<5){
    printf("USAGE: ./dual-fast-v19 instance cutoff seed alpha [K] [rho] [q0] [beta]\n");
    return 0;
  }
  build_instance_massive(argv[1]);

  if(vertex_num<10000)
    timeout=0.1;
  else if(vertex_num<100000)
    timeout=0.3;
  else if(vertex_num<500000)
    timeout=0.5;
  else
    timeout=5.0;
    
  time_limit=atof(argv[2]);
  seed=atoi(argv[3]);
  ALPHA=1+ atoi(argv[4])/100.0;

  if(argc>5) AQ_NUM_ANTS = atoi(argv[5]);
  if(argc>6) AQ_RHO     = atof(argv[6]);
  if(argc>7) AQ_Q0      = atof(argv[7]);
  if(argc>8) AQ_BETA    = atof(argv[8]);
  const char *aq_mode = getenv("MWDS_AQ_MODE");
  int force_dbs = (aq_mode && strcmp(aq_mode, "dbs") == 0);
  const char *safe_min_gap_env = getenv("MWDS_AQ_MIN_FIRST_GAP");
  const char *safe_min_nodes_env = getenv("MWDS_AQ_MIN_NODES");
  double aq_min_first_gap = safe_min_gap_env ? atof(safe_min_gap_env) : 0.05;
  int aq_min_nodes = safe_min_nodes_env ? atoi(safe_min_nodes_env) : 800;

  total_step=INT_MAX;
  printf("%s #seed %d #alpha %.3lf #timeout %.3lf K=%d RHO=%.2f Q0=%.2f BETA=%.1f AQ_MODE=%s SAFE_AQ_MIN_GAP=%.3f SAFE_AQ_MIN_NODES=%d\n",
         argv[1], seed, ALPHA, timeout, AQ_NUM_ANTS, AQ_RHO, AQ_Q0, AQ_BETA,
         aq_mode ? aq_mode : "auto", aq_min_first_gap, aq_min_nodes);
  srand(seed);
  read_time=get_utime();

  init();
  init_reduce();
  init_after_reduction();
  double density = (double)NB_EDGE / NB_NODE;
  USE_ADVANCED = (NB_NODE >= 800) ? 1 : 0;
  printf("[v19] |V|=%d |E|=%d density=%.2f USE_ADVANCED=%d\n", NB_NODE, NB_EDGE, density, USE_ADVANCED);

  WeightSum prev_best_lb = 0;
  int lb_stagnation = 0;
  int lb_converged = 0;

  printf("#Rd        #LB        #LB*       #UB       #Time        #UB+        #UB*      #Time      #TotalTime\n");
  while(1){
    reset_config();
    if(BEST_BEST_LOWER_BOUND==best_best_value
       || get_utime()-read_time>time_limit
       || ibmwds_init_bounds(i++,&timeout)){  
      break;
    }
    double time_left= time_limit-(get_utime()-read_time);
    if(time_left<0)
      break;

    if(force_dbs){
      AQ_ENABLED = 0;
      AQ_ACTIVE = 0;
      AQ_TOUCH_UB = 0;
    }else if(i==1 && FIRST_GAP >= gap_thd){
      double rl_deadline;
      if(NB_NODE < aq_min_nodes || FIRST_GAP < aq_min_first_gap){
        printf("\n [Online-safe AQ eligibility guard] gap=%.4lf density=%.2lf |V|=%d => No RL\n",
               FIRST_GAP, density, NB_NODE);
        AQ_ENABLED = 0;
        AQ_ACTIVE = 0;
        AQ_TOUCH_UB = 0;
        rl_deadline = 0;
      } 
      else if(FIRST_GAP <= 0.5 && density <= 10.0){
        printf("\n [Tier-2 Medium] gap=%.4lf density=%.2lf |V|=%d => Standard RL (K=%d, 15%%)\n",
               FIRST_GAP, density, NB_NODE, AQ_NUM_ANTS);
        AQ_ENABLED = 1;
        AQ_ACTIVE = 1;
        AQ_TOUCH_UB = 0;
        rl_deadline = time_limit * 0.15;
      } 
      else {
        int hard_K = (NB_NODE > 100000) ? 10 : 8;
        AQ_NUM_ANTS = hard_K;
        AQ_RHO = 0.08f;
        printf("\n [Tier-3 Hard] gap=%.4lf density=%.2lf |V|=%d => Heavy RL (K=%d, 25%%)\n",
               FIRST_GAP, density, NB_NODE, AQ_NUM_ANTS);
        AQ_ENABLED = 1;
        AQ_ACTIVE = 1;
        AQ_TOUCH_UB = 0;
        rl_deadline = time_limit * 0.25;
      }
      if(rl_deadline > 0){
        WeightSum rl_prev_lb = BEST_BEST_LOWER_BOUND;
        int rl_stag = 0;
        while(get_utime()-read_time < rl_deadline){
          reset_config();
          if(ibmwds_init_bounds(i++,&timeout))
            break;
          if(BEST_BEST_LOWER_BOUND > rl_prev_lb){
            rl_prev_lb = BEST_BEST_LOWER_BOUND;
            rl_stag = 0;
          } else {
            rl_stag++;
          }
          if(rl_stag >= 2){
            printf(" [AQ guard] no early LB gain, disabling AQ\n");
            AQ_ENABLED = 0;
            AQ_ACTIVE = 0;
            AQ_TOUCH_UB = 0;
            break;
          }
        }
        AQ_NUM_ANTS = 1;
      }
    }

    if(USE_ADVANCED){
      if(BEST_BEST_LOWER_BOUND > prev_best_lb){
        lb_stagnation = 0;
        prev_best_lb = BEST_BEST_LOWER_BOUND;
      } else {
        lb_stagnation++;
      }

      double elapsed_ratio = (get_utime()-read_time) / time_limit;
      if(!lb_converged && lb_stagnation >= 3 && elapsed_ratio > 0.4){
      //尚未切换过 且 连续3轮没进展 且 时间已过40%，把剩余全部时间交给UB局部搜索
        lb_converged = 1;
        double remaining = time_limit - (get_utime()-read_time);
        printf("\n [LB Done] stag=%d elapsed=%.1f%% => %.1fs to UB\n",
               lb_stagnation, elapsed_ratio*100, remaining);
        if(remaining > 0){
          init_solution();
          localsearch(remaining);
          if(!check()){
            printf("wrong answer \n");
            break;
          }
          USED(UNIT_STK)=0;
          for(int ii=0,v;ii<remain_num;ii++){
            v= remain_vertex[ii];
            #ifdef SOL
            if(best_sol[v]==1){
              v=v+1;
              push_back(UNIT_STK,int,v);;
            }
            #else
            if(reduce[v]==1){
              v=v+1;
              push_back(UNIT_STK,int,v);
            }
            #endif
          }
        }
        break;
      }
    }

    time_left = time_limit-(get_utime()-read_time);
    if(time_left<0) break;
    if(time_left<timeout) timeout=time_left;

    init_solution();
    localsearch(timeout);
    if(!check()) {
      printf("wrong answer \n");
      break;
    }
 
    USED(UNIT_STK)=0;
    for(int ii=0,v;ii<remain_num;ii++){
      v= remain_vertex[ii];
      #ifdef SOL 
      if(best_sol[v]==1){
	v=v+1;
	push_back(UNIT_STK,int,v);;
      }
      #else
      if(reduce[v]==1){
	v=v+1;
	push_back(UNIT_STK,int,v);
      }
      #endif
    }
  }

  if(best_best_value==LONG_MAX)
    best_best_value=BEST_UPPER_BOUND;
  double lgap= (BEST_BEST_LOWER_BOUND-FIRST_LOWER_BOUND)/(double)FIRST_LOWER_BOUND;
  double ugap= (FIRST_UPPER_BOUND-best_best_value)/(double)FIRST_UPPER_BOUND;
  double gap=(best_best_value-BEST_BEST_LOWER_BOUND)/(double)BEST_BEST_LOWER_BOUND;
  if(gap!=0)
    printf(">>> %s |V| %d |E| %d  (#LB %0.4lf %lld ---> %lld  %0.4lf  %ld <--- %lld  %.4lf #UB)  #solve_ime %.4lf read_time %.4lf \n"
	   , getInstanceName(argv[1]),NB_NODE,NB_EDGE,lgap, FIRST_LOWER_BOUND, BEST_BEST_LOWER_BOUND,gap, best_best_value,FIRST_UPPER_BOUND,ugap, get_utime()-read_time,read_time);
  else

    printf("\n>>> %s |V| %d |E| %d  (#LB %0.4lf %lld ---> %lld  ====  %ld <--- %lld  %.4lf #UB)  #solve_ime %.4lf read_time %.4lf  \n"
	   , getInstanceName(argv[1]),NB_NODE,NB_EDGE,lgap, FIRST_LOWER_BOUND, BEST_BEST_LOWER_BOUND, best_best_value,FIRST_UPPER_BOUND,ugap, get_utime()-read_time,read_time);
   
	
  free_all();
  return 0;
}
