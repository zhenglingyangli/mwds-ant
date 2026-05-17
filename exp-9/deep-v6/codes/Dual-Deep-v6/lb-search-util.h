#include "basic.h"
#include "util_heap.h"
#include "util_vector.h"
#include <sys/resource.h>
#define WORD_LENGTH 100
#define TRUE 1
#define FALSE 0
#define NONE 0
#define DELIMITER 0
#define PASSIVE 0
#define ACTIVE 1
#define MAX_NODE 120000000
#define MAX_WEIGHT 999999999
#define MAX_2IS_SIZE 500
#define MAXIS 16
#define WeightSum long long

#ifndef SIG64
#define set_neighbor_bit(node,neibor) (SIG[node]|=1<<(neibor%32))
#define fast_2adj(node1,node2) (SIG[node1]&SIG[node2])
#else
 #define set_neighbor_bit(node,neibor) \
  do{ \
    int _idx=neibor%64;\
    if(_idx<32)\
      SIG[node].sig1|=1<<(_idx);\
    else 					\
      SIG[node].sig2|=1<<(_idx-32);\
 }while(0)
 #define fast_2adj(node1,node2) ((SIG[node1].sig1&SIG[node2].sig1)||(SIG[node1].sig2&SIG[node2].sig2))
#endif

#define for_each_vertex(node) for(int node=1;node<=NB_NODE;node++)
#define for_each_neighbor(__vertex,__neibor)  for(int * __ptr=Node_Neibors[__vertex],__neibor=*__ptr;__neibor!=NONE;__neibor=*(++__ptr))

#define for_each_neighbor2(__vertex,__neibor)  for(int * __ptr2=Node_Neibors[__vertex],__neibor=*__ptr2;__neibor!=NONE;__neibor=*(++__ptr2))

#define for_each_2hop_neighbor(__vertex,__neibor)  for(int * __ptr=Node_2Neibors[__vertex],__neibor=*__ptr;__neibor!=NONE;__neibor=*(++__ptr))


#define for_each_undomed_node(node)   for(int __i=SUB_PROBLEM_SIZE-1,node=CFG[__i];__i>=CUR_UND_IDX;node=CFG[--__i])

#define for_each_undomed_node2(node)  for(int __i=CUR_UND_IDX,node=CFG[__i];__i<SUB_PROBLEM_SIZE;node=CFG[++__i])


#define domed(node) (STATUS[node].dominated)
#define clr_domed_status(node) (STATUS[node].dominated=0)
#define set_domed_status(node) (STATUS[node].dominated=1)

#define fixed(node) (STATUS[node].fixed)
#define deleted(node) (STATUS[node].deleted)

#define minimal(node) (STATUS[node].minimal)

#define branched(node) (STATUS[node].value==V_FALSE)
#define set_branched_status(node) (STATUS[node].value=V_FALSE)
#define clr_branched_status(node) (STATUS[node].value=V_UNDEF)

#define value(node) (STATUS[node].value)
#define clr_value(node) (STATUS[node].value=V_UNDEF)



#define unitp(node) (STATUS[node].implied)


#define included(node)  (STATUS[node].included)
#define set_included_status(node)  (STATUS[node].included=1)
#define clr_included_status(node)  (STATUS[node].included=0)

#define bit_set(vec,idx) ((*(vec+(idx>>5)))|= (1<<(idx&31)))
#define bit_clr(vec,idx) ((*(vec+(idx>>5)))&= (~(1<<(idx&31))))
#define bit_val(vec,idx) ((*(vec+(idx>>5)))&(1<<(idx&31)))

#define CUR_BRA_IDX   BRAIDX[CUR_LEVEL]
#define CUR_BRA_NODE  ITEM(BRA_STK,CUR_BRA_IDX)
//#define move_next()  CUR_BRA_IDX++,CUR_BRA_NODE 
#define NEXT_BRA_NODE  ITEM(BRA_STK,CUR_BRA_IDX+1)
#define NEXT_NEXT_BRA_NODE  ITEM(BRA_STK,CUR_BRA_IDX+2)
#define CUR_LEVEL_UND_IDX  UNDIDX[CUR_LEVEL]
#define adjlen(node) ((node)/32+1)

#define marked(node) (PID[node].marked)
#define set_marked_status(node) (PID[node].marked=1)
#define clr_marked_status(node) (PID[node].marked=0)

#define loved(node) (PID[node].loved)
#define set_loved_status(node) (PID[node].loved=1)
#define clr_loved_status(node) (PID[node].loved=0)

#define touched(node) (PID[node].touched)
#define set_touched_status(node) (PID[node].touched=1)
#define clr_touched_status(node) (PID[node].touched=0)

#define selected(node) (PID[node].selected)
#define set_selected_status(node) (PID[node].selected=1)
#define clr_selected_status(node) (PID[node].selected=0)
  
#define involved(node) (PID[node].involved)
#define set_involved_status(node) (PID[node].involved=1)
#define clr_involved_status(node) (PID[node].involved=0)
#define set_newid(node,id)  (PID[node].newid=id)
#define set_isno(node,no)  (PID[node].isno=no)


#define newid(node)  (PID[node].newid)
#define isno(node)  (PID[node].isno)

#define branch_node_at_level(i) ITEM(BRA_STK,BRAIDX[i])


typedef struct{
  unsigned sig1;
  unsigned sig2;
}AdjSign;


typedef struct{
  int target;
  int select;
  int delta;
  int replaced;
}LBPair;

static LBPair  *PairList;
static int PairLength=0;
static int *PairIndex;

#define V_TRUE 1
#define V_FALSE 0
#define V_UNDEF 2



typedef struct{
  unsigned char fixed:1;
  unsigned char implied:1;
  unsigned char deleted:1;
  unsigned char minimal:1;
  unsigned char included:1;
  unsigned char dominated:1;
  unsigned char value:2;
}VSTATUS;

typedef struct{
 unsigned char involved:1;
 unsigned char marked:1;
 unsigned char touched:1;
 unsigned char selected:1;
 unsigned char loved:1;
 unsigned char isno:3;
}PSTATUS;


static int CUT_SUM=0,UP_SUM=0,SOL_NO=0; 

static int INT_NONE=NONE;

static int OPTIMAL=0;

static int * Init_Adj_List;

static int BLOCK_COUNT = 0;
static int *BLOCK_LIST[100];
static int **Node_Neibors;
static int **Touch_Deltas;


static int **Node_2Neibors;

static unsigned  *Node_Weight;
static unsigned  *Node_Delta;
static unsigned  *DomCost;
static WeightSum *DomSum;
static unsigned  *DeltaCost;
static int  *ZeroTouch;

static int  *DomedNumber;
static int  *DomedReason;
static int  *MinNeibor;
static int  *MinNeiborBak;
static int  *Loss,*Loss_Bak;
static int  *Subs,*Subs_Bak;
static float *Beta;

/*------------------------------------------------------------
 * AntQO v1: AQ 值及相关全局变量
 *
 * AQ(v) 是每个顶点的历史经验偏好值，跨迭代、跨 DBS round 持久保留。
 * 在排序构造时，HEUR'(v) = HEUR(v) * AQ(v)，引导选择。
 *-----------------------------------------------------------*/
static float *AQ;

static float AQ_TAU0     = 1.0f;
static float AQ_RHO      = 0.05f;
static float AQ_Q0       = 0.9f;
static float AQ_TAU_MIN  = 0.01f;
static float AQ_TAU_MAX  = 20.0f;
static float AQ_LAMBDA   = 0.3f;
static float AQ_BETA     = 3.0f;
static int   AQ_NUM_ANTS = 5;

static int   AQ_PHASE = 1;
static int   AQ_ENABLED = 0;
static int   USE_ADVANCED = 0;

static LBPair *BestAnt_PairList;
static int     BestAnt_PairLength;
static WeightSum BestAnt_LB;
static double    BestAnt_Score;

static int AQ_Stagnation       = 0;
static int AQ_RESTART_THRESHOLD = 10;

static unsigned *Node_Degree;

static int NB_NODE,NB_EDGE,ACTIVE_EDGE,ACTIVE_NODE, Max_Degree = 0, Max_Degree_Node,SUB_PROBLEM_SIZE;
static int FORMAT = 1,  NB_NODE_O,  NB_EDGE_O;
static double READ_TIME, INIT_TIME, SEARCH_TIME;
static int INIT_BRANCHING_NODE=0;
static WeightSum INIT_UPPER_BOUND=0;
static unsigned long long NB_TREE=0,NB_CUT=0;

static int * CFG;
static int * LOC;
static int * UBC;

#ifndef SIG64
static unsigned * SIG;
#else
static AdjSign *SIG;
#endif

static char *INSTANCE;

static int * BRAIDX;
static int * UNDIDX;
static VEC_INT * BRA_STK;
static VEC_INT * UNIT_STK;
static VEC_INT * PART_STK;

static WeightSum  BEST_UPPER_BOUND,CUR_BOUND,LOWER_BOUND,BEST_LOWER_BOUND=0,BEST_BEST_LOWER_BOUND=0,LOWER_BOUND_MAT;
static int CUR_LEVEL,CUR_UND_IDX;
static VSTATUS * STATUS;
static PSTATUS * PID;
//static int * ADJIDX;
//static VEC_UINT * ADJ_STK;
static int TIME_OUT, CUT_OFF=0;
static double BEST_SOL_TIME;
static char instance[1024]={'\0'};
static VEC_INT *iSET[MAXIS+1];
//static int iSET_Counter[MAXIS+1];
static int iSET_Status[MAXIS+1];
static int iSET_Insert[MAXIS+1];
static WeightSum iSET_Weight[MAXIS+1];
static float *Node_Score;
static double OPT_Tolerance=0.001;
//parameter for optcc and unit_propagate
static int enable_cc=0,CC_THD=0;
static int enable_up=0,UP_THD=0;
static int lbrate=0;
static float lbr=1.0f;

static int INIT_TREE_DEPTH;
static WeightSum FIRST_LOWER_BOUND=0;
static WeightSum FIRST_UPPER_BOUND=0;
static double FIRST_GAP=0;

static double get_utime() {
  struct rusage utime;
  getrusage(RUSAGE_SELF, &utime);
  return (double) (utime.ru_utime.tv_sec
		   + (double) utime.ru_utime.tv_usec / 1000000);
}

static VEC_INT * FIX_STK;
static VEC_INT * VEC_SUBGRAPHS;
static VEC_INT * VEC_SOLUTION;
static VEC_INT * VEC_PARTIAL;
static int NB_FIXED=0,NEW_IDX=0,NB_UNFIXED=0;
static float DTIMES=3,DRATE;
static int MaxIteration=20;

static void allcoate_memory_for_adjacency_list(int nb_node, int nb_edge,int offset) {
  int i, block_size = 40960000, free_size = 0;
  Init_Adj_List = (int *) malloc((2 * nb_edge + nb_node) * sizeof(int));
  if (Init_Adj_List == NULL ) {
    for (i = 1; i <= NB_NODE; i++) {
      if (Node_Degree[i - offset] + 1 > free_size) {
	Node_Neibors[i] = (int *) malloc(block_size * sizeof(int));
	BLOCK_LIST[BLOCK_COUNT++] = Node_Neibors[i];
	free_size = block_size - (Node_Degree[i - offset] + 1);
      } else {
	Node_Neibors[i] = Node_Neibors[i - 1]
	  + Node_Degree[i - 1 - offset] + 1;
	free_size = free_size - (Node_Degree[i - offset] + 1);
      }
    }
  } else {
    BLOCK_COUNT = 1;
    BLOCK_LIST[BLOCK_COUNT - 1] = Init_Adj_List;
    Node_Neibors[1] = Init_Adj_List;
    for (i = 2; i <= NB_NODE; i++) {
      Node_Neibors[i] = Node_Neibors[i - 1] + Node_Degree[i - 1 - offset]
	+ 1;
    }
  }
}

static int _read_graph_wclq_format(int nb_node,int nb_edge,int v_Deg[], int * v_Adj[],int v_Cost[]) {

        int max_weight=0;

	//	memset(Node_Degree, 0, MAX_NODE * sizeof(unsigned));
	
	NB_NODE = nb_node;
	NB_EDGE = nb_edge;
	if (NB_NODE > MAX_NODE) {
		printf("R the graph goes beyond the max size can be processed: %d\n", NB_NODE);
		exit(0);
	}

	//printf(">>IBM: |V|=%d |E|=%d\n", NB_NODE,nb_edge);
	Node_Degree=(unsigned *) malloc((NB_NODE + 1) * sizeof(unsigned));
	Node_Weight=(unsigned *) malloc((NB_NODE + 1) * sizeof(unsigned));
	Node_Delta=(unsigned *) malloc((NB_NODE + 1) * sizeof(unsigned));
	DomCost=(unsigned *) malloc((NB_NODE + 1) * sizeof(unsigned));
	DeltaCost=(unsigned *) malloc((NB_NODE + 1) * sizeof(unsigned));
	//	ZeroTouch=(int *) malloc((NB_NODE + 1) * sizeof(int));
	Node_Neibors = (int **) malloc((NB_NODE + 1) * sizeof(int *));
	Max_Degree = 0;
	
        for (int v = 1; v <= NB_NODE; v++) {
	  Node_Degree[v]=v_Deg[v];
	  Node_Weight[v]=v_Cost[v];
	  //printf("%d %d %d\n",v,v_Deg[v],v_Cost[v]);
	  if (Node_Degree[v] > Max_Degree)
	    Max_Degree = Node_Degree[v];
	  if (Node_Weight[v] > max_weight)
	    max_weight = Node_Weight[v];
	}

	allcoate_memory_for_adjacency_list(NB_NODE, nb_edge, 0);
	
	for (int v = 1; v <= NB_NODE; v++) {
	  for(int i=0;i<v_Deg[v];i++){
	    Node_Neibors[v][i] = v_Adj[v][i];
	  }
	  Node_Neibors[v][v_Deg[v]]=NONE;
	}
	//printf(">>IBM: The maximum node weight is %d\n",max_weight);
	return TRUE;
}


static char * getInstanceName(char *s) {
  if (strrchr(s, '/') == NULL )
    return s;
  else
    return strrchr(s, '/') + 1;
}


//static int *dfn,*low,*TarStack,TarTop,CNT=0,*SonNum,*RecSta,RecTop,*LasSon,*LasNodeIndex;

//After preprocess, following variables might still be useful:
//static int *SubGraph_size,NB_DCC=0,*InDcc,NB_cut=0;
//static double REDUCE_TIME=0;



static inline void swap_cfg(int a, int b){
  CFG[LOC[b]]=a;
  CFG[LOC[a]]=b;
  int t=LOC[a];
  LOC[a]=LOC[b];
  LOC[b]=t;
}

static inline void update_node_delta(int by_node,int base_cost){
  Node_Delta[by_node]-=base_cost;
  int delta= Node_Delta[by_node];
  assert(delta>=0);

  if(!domed(by_node)){
    if(delta<DeltaCost[by_node]){
      DeltaCost[by_node]=delta;
      MinNeibor[by_node]=by_node;
    }
  }
  for_each_neighbor(by_node,neibor){
    if(!domed(neibor)){
      if(delta<DeltaCost[neibor]){
	DeltaCost[neibor]=delta;
	MinNeibor[neibor]=by_node;
      }
    }
  }
}


WeightSum compute_upper_bound(){
  int undomed=0;
  memset(Node_Score,0,(NB_NODE+1)*sizeof(float));
 
  for_each_undomed_node(node){
    if(!domed(node)){
      undomed++;
      Node_Score[node]+=Node_Weight[node];
      for_each_neighbor(node,neibor){
	if(!branched(neibor))
	  Node_Score[neibor]+=Node_Weight[node];
      }
    }
  }
  int *ptr=CFG;
  WeightSum total=0;
  clearHeap(Node_Heap);
  for(int node=*ptr;node!=NONE;node=*(++ptr)){
   if(fixed(node) || Node_Score[node]==0)continue;
   float ub_priority = Node_Score[node]/Node_Weight[node];
   if(AQ_PHASE == 2)
     ub_priority *= powf(AQ[node], AQ_BETA * 0.3f);
   insertHeap(Node_Heap,node,ub_priority);
  }
 
  while(undomed>0){
    HeapNode temp=removeTop(Node_Heap);
    int bnode=temp.key;
    float _val=Node_Score[bnode]/Node_Weight[bnode];
    if (temp.value!=_val){
      temp.value=_val;
      insertHeap(Node_Heap,bnode,_val);
      continue;
    }
    assert(bnode);
    assert(!fixed(bnode));
    assert(Node_Score[bnode]>0);
    total+=Node_Weight[bnode];
    push_back(VEC_PARTIAL,int,bnode);
    for_each_neighbor(bnode,neibor){
      assert(!deleted(neibor));
      if(!domed(neibor)){
	undomed--;
	set_domed_status(neibor);
	int _w=Node_Weight[neibor];
	for_each_neighbor(neibor,nei){
	  if(!fixed(nei))
	    Node_Score[nei]-=_w;
	}
	Node_Score[neibor]-=_w;
      }
    }
    if(!domed(bnode)){
      undomed--;
      set_domed_status(bnode);
      for_each_neighbor(bnode,nei){
	if(!fixed(nei)&& !branched(nei))
	  Node_Score[nei]-=Node_Weight[bnode];
      }
    }
    Node_Score[bnode]=0;
  }
  #ifdef CHECK
  for(int node=1;node<=NB_NODE;node++)
    if(!deleted(node))
      assert(domed(node));
  #endif
   return total;
}

static int exact_small_dom_checked = 0;
static WeightSum exact_small_dom_lb = 0;
static WeightSum exact_small_dom_ub = 0;
static int exact_small_dom_node1 = 0;
static int exact_small_dom_node2 = 0;
static int exact_small_dom_solution[65];
static int exact_small_dom_solution_size = 0;

static int exact64_n;
static unsigned long long exact64_closed[64];
static unsigned exact64_weight[64];
static int exact64_node[64];
static int exact64_cands[64][64];
static int exact64_cand_count[64];
static WeightSum exact64_best;
static int exact64_best_sol[64];
static int exact64_best_size;
static int exact64_cur_sol[64];
static int exact64_nodes;
static int exact64_abort;
static double exact64_start;

static inline int exact_bit_count(unsigned long long x);

static int exact64_better_candidate(int a, int b){
  if(exact64_weight[a] != exact64_weight[b])
    return exact64_weight[a] < exact64_weight[b];
  return exact_bit_count(exact64_closed[a]) > exact_bit_count(exact64_closed[b]);
}

static inline int exact_bit_count(unsigned long long x){
  return __builtin_popcountll(x);
}

static inline void exact_set_bit(unsigned long long *row, int idx){
  row[idx >> 6] |= (1ULL << (idx & 63));
}

static int exact64_choose_uncovered(unsigned long long covered){
  int best_u = -1;
  int best_count = 1000000;
  for(int u = 0; u < exact64_n; u++){
    if((covered >> u) & 1ULL)
      continue;
    if(exact64_cand_count[u] < best_count){
      best_count = exact64_cand_count[u];
      best_u = u;
    }
  }
  return best_u;
}

static void exact64_search(unsigned long long covered, WeightSum cost, int depth){
  exact64_nodes++;
  if((exact64_nodes & 8191) == 0){
    if(exact64_nodes > 2000000 || get_utime() - exact64_start > 0.25){
      exact64_abort = 1;
      return;
    }
  }
  if(cost >= exact64_best)
    return;
  if(covered == ((exact64_n == 64) ? ~0ULL : ((1ULL << exact64_n) - 1ULL))){
    exact64_best = cost;
    exact64_best_size = depth;
    for(int i = 0; i < depth; i++)
      exact64_best_sol[i] = exact64_cur_sol[i];
    return;
  }
  int u = exact64_choose_uncovered(covered);
  if(u < 0)
    return;
  for(int ci = 0; ci < exact64_cand_count[u]; ci++){
    int v = exact64_cands[u][ci];
    unsigned long long next = covered | exact64_closed[v];
    if(next == covered)
      continue;
    exact64_cur_sol[depth] = v;
    exact64_search(next, cost + exact64_weight[v], depth + 1);
    if(exact64_abort)
      return;
  }
}

static int compute_exact64_weighted_dom_certificate(){
  exact_small_dom_solution_size = 0;
  exact64_n = 0;
  for_each_vertex(node){
    if(deleted(node))
      continue;
    if(fixed(node))
      return 0;
    if(exact64_n >= 64)
      return 0;
    exact64_node[exact64_n] = node;
    exact64_weight[exact64_n] = Node_Weight[node];
    exact64_n++;
  }
  if(exact64_n <= 0)
    return 0;

  for(int i = 0; i < exact64_n; i++){
    int node = exact64_node[i];
    exact64_closed[i] = (1ULL << i);
    for_each_neighbor(node, neibor){
      for(int j = 0; j < exact64_n; j++){
        if(exact64_node[j] == neibor){
          exact64_closed[i] |= (1ULL << j);
          break;
        }
      }
    }
  }

  for(int u = 0; u < exact64_n; u++){
    exact64_cand_count[u] = 0;
    for(int v = 0; v < exact64_n; v++){
      if((exact64_closed[v] >> u) & 1ULL)
        exact64_cands[u][exact64_cand_count[u]++] = v;
    }
    for(int i = 1; i < exact64_cand_count[u]; i++){
      int key = exact64_cands[u][i];
      int j = i - 1;
      while(j >= 0 && exact64_better_candidate(key, exact64_cands[u][j])){
        exact64_cands[u][j + 1] = exact64_cands[u][j];
        j--;
      }
      exact64_cands[u][j + 1] = key;
    }
  }

  unsigned long long covered = 0;
  exact64_best = 0;
  exact64_best_size = 0;
  while(covered != ((exact64_n == 64) ? ~0ULL : ((1ULL << exact64_n) - 1ULL))){
    int best = -1;
    double best_ratio = -1.0;
    for(int v = 0; v < exact64_n; v++){
      int gain = exact_bit_count(exact64_closed[v] & ~covered);
      double ratio = gain / (double)exact64_weight[v];
      if(gain > 0 && ratio > best_ratio){
        best_ratio = ratio;
        best = v;
      }
    }
    if(best < 0)
      return 0;
    exact64_best += exact64_weight[best];
    exact64_best_sol[exact64_best_size++] = best;
    covered |= exact64_closed[best];
  }

  exact64_nodes = 0;
  exact64_abort = 0;
  exact64_start = get_utime();
  exact64_search(0ULL, 0, 0);
  if(exact64_abort || exact64_best <= 0)
    return 0;

  exact_small_dom_lb = exact64_best;
  exact_small_dom_ub = exact64_best;
  exact_small_dom_node1 = 0;
  exact_small_dom_node2 = 0;
  exact_small_dom_solution_size = exact64_best_size;
  for(int i = 0; i < exact64_best_size; i++)
    exact_small_dom_solution[i] = exact64_node[exact64_best_sol[i]];
  return 1;
}

static WeightSum compute_exact_small_weighted_dom_lb(){
  if(exact_small_dom_checked)
    return exact_small_dom_lb;
  exact_small_dom_checked = 1;
  exact_small_dom_lb = 0;
  exact_small_dom_ub = 0;
  exact_small_dom_node1 = 0;
  exact_small_dom_node2 = 0;
  exact_small_dom_solution_size = 0;

  if(compute_exact64_weighted_dom_certificate())
    return exact_small_dom_lb;

  int active = 0;
  for_each_vertex(node){
    if(deleted(node))
      continue;
    if(fixed(node))
      return exact_small_dom_lb;
    active++;
  }
  if(active <= 0 || active > 2500)
    return exact_small_dom_lb;

  int *active_nodes = (int *)malloc(active * sizeof(int));
  int *pos = (int *)malloc((NB_NODE + 1) * sizeof(int));
  if(!active_nodes || !pos){
    if(active_nodes) free(active_nodes);
    if(pos) free(pos);
    return exact_small_dom_lb;
  }
  for(int i = 0; i <= NB_NODE; i++)
    pos[i] = -1;
  int idx = 0;
  for_each_vertex(node){
    if(!deleted(node)){
      active_nodes[idx] = node;
      pos[node] = idx++;
    }
  }

  int words = (active + 63) >> 6;
  unsigned long long *closed = (unsigned long long *)calloc((size_t)active * words, sizeof(unsigned long long));
  if(!closed){
    free(active_nodes);
    free(pos);
    return exact_small_dom_lb;
  }

  for(int i = 0; i < active; i++){
    int node = active_nodes[i];
    unsigned long long *row = closed + (size_t)i * words;
    exact_set_bit(row, i);
    for_each_neighbor(node, neibor){
      int p = (neibor >= 1 && neibor <= NB_NODE) ? pos[neibor] : -1;
      if(p >= 0)
        exact_set_bit(row, p);
    }
  }

  WeightSum min_dom_cost = 0;
  for(int i = 0; i < active; i++){
    int count = 0;
    unsigned long long *row = closed + (size_t)i * words;
    for(int w = 0; w < words; w++)
      count += exact_bit_count(row[w]);
    if(count == active){
      WeightSum cost = Node_Weight[active_nodes[i]];
      if(min_dom_cost == 0 || cost < min_dom_cost){
        min_dom_cost = cost;
        exact_small_dom_node1 = active_nodes[i];
        exact_small_dom_node2 = 0;
      }
    }
  }

  for(int i = 0; i < active; i++){
    unsigned long long *row_i = closed + (size_t)i * words;
    for(int j = i + 1; j < active; j++){
      unsigned long long *row_j = closed + (size_t)j * words;
      int count = 0;
      for(int w = 0; w < words; w++)
        count += exact_bit_count(row_i[w] | row_j[w]);
      if(count == active){
        WeightSum cost = Node_Weight[active_nodes[i]] + Node_Weight[active_nodes[j]];
        if(min_dom_cost == 0 || cost < min_dom_cost){
          min_dom_cost = cost;
          exact_small_dom_node1 = active_nodes[i];
          exact_small_dom_node2 = active_nodes[j];
        }
      }
    }
  }

  if(min_dom_cost > 0){
    exact_small_dom_ub = min_dom_cost;
    exact_small_dom_solution_size = 0;
    if(min_dom_cost <= 1)
      exact_small_dom_lb = 1;
    else if(min_dom_cost <= 2)
      exact_small_dom_lb = 2;
    else
      exact_small_dom_lb = 3;
  }else{
    exact_small_dom_lb = 3;
  }
  free(closed);
  free(active_nodes);
  free(pos);
  return exact_small_dom_lb;
}


static inline void update_best_solution(){
  USED(VEC_SOLUTION)=0;
  WeightSum bound=0;
  for(int i=0;i<USED(VEC_PARTIAL);i++){
    int node=ITEM(VEC_PARTIAL,i);
    //assert(value(node)==V_TRUE);
    bound+=Node_Weight[node];
    push_back(VEC_SOLUTION,int,node);
  }
  // printf("bound %d BEST_UPPER_BOUND %d\n ",bound,BEST_UPPER_BOUND);
  assert(bound==BEST_UPPER_BOUND);
}

static double CUR_GAP=0.0;
static int compute_loss_and_upper_bound(WeightSum lb){

  WeightSum ub=CUR_BOUND;
  USED(VEC_PARTIAL)=NB_FIXED;
  for(int i=PairLength-1;i>=0;i--){
    if(PairList[i].replaced>0){
      if(PairList[i].replaced>1)
	Subs[PairList[i].target]+=PairList[i].replaced-1;
    }
    else{
      assert(PairList[i].replaced==0);
      int select_node=PairList[i].select;
      ub+=Node_Weight[select_node];
      push_back(VEC_PARTIAL,int,select_node);
      set_domed_status(select_node);
      if(selected(select_node)){
	int j=PairIndex[select_node];
	if(j<i){
	  PairList[j].replaced++;
	}
      }
      for_each_neighbor(select_node,neibor){
	set_domed_status(neibor);
	if(selected(neibor)){
	  int j=PairIndex[neibor];
	  if(j<i){
	    PairList[j].replaced++;
	  }
	}
      }
    }
  }
  int opt=0,rep_flag=0,loss_sum=0;
  for(int i=0;i<PairLength;i++){
    if(PairList[i].replaced){
      if(PairList[i].replaced>1)
	rep_flag=1;
      int node=PairList[i].select,count=0;
      if(!domed(node))count++;
      for_each_neighbor(node,neibor){
	if(!domed(neibor)){
	  count++;
	}
      }
      Loss[PairList[i].target]+=count;
      loss_sum+=count;
    }      
  }
  //printf("lb %lld ub %lld\n",lb,ub);
  assert(lb<=ub);
  ub+=compute_upper_bound();
  assert(BEST_LOWER_BOUND<=ub);
  opt=0;  
  if(ub<BEST_UPPER_BOUND){
    BEST_UPPER_BOUND=ub;
    update_best_solution();
    opt=1;
  }
    
  assert(BEST_UPPER_BOUND>=BEST_LOWER_BOUND);
    
  /*
   * exp-9: only a tight LB/UB equality should terminate the bound search.
   * A no-replacement/no-loss ordering is not proof that later Beta/AQ rounds
   * cannot lift the lower bound; exp-8 stopped too early on dense/structured
   * instances while LB was still strictly below UB.
   */
  if(BEST_UPPER_BOUND==BEST_LOWER_BOUND)
    OPTIMAL=1;
    
 
   return OPTIMAL;
}


#define H9

#ifdef H1
#define HEUR(node) (DeltaCost[node]/sqrt((float)UBC[node]))
#endif
#ifdef H2
#define HEUR(node) (DeltaCost[node]/(sqrt((float)(UBC[node]-1))+sqrt((float)Node_Degree[MinNeibor[node]])))
#endif

#ifdef H3
#define HEUR(node) (1/((float)UBC[node]))
#endif


#ifdef H4
#define HEUR(node)  (DeltaCost[node]/(sqrt((float)Lost[MinNeibor[node]])+sqrt((float)(UBC[node]-1))+sqrt((float)Node_Degree[MinNeibor[node]])))
#endif


#ifdef H5
#define HEUR(node) (DeltaCost[node]/(sqrt((float)Lost[MinNeibor[node]])+sqrt((float)(UBC[node]-1))))
#endif

#ifdef H6
#define HEUR(node) (DeltaCost[node]/(sqrt((float)((Loss[node]+1)*Subs[node]*(UBC[node]-1)))))
#endif


#define term1(node) sqrt((float)((Loss[node]+1)*Subs[node]))
#define term2(node) sqrt((float)(UBC[node]-1))
#define term3(node) sqrt((float)Node_Degree[MinNeibor[node]])

#ifdef H7
#define HEUR(node) (DeltaCost[node]/(term1(node)*(term2(node)+term3(node))))
#endif

#define alpha(node) ((float)DeltaCost[node]/Node_Weight[node])

#ifdef H8
#define HEUR(node) (DeltaCost[node]/(term1(node)*(term2(node)+term3(node))))*alpha(node)
#endif


#ifdef H9
#define HEUR(node) ((Beta[node]*DeltaCost[node])/(term1(node)*(term2(node)+term3(node)))*(AQ_PHASE==1 ? 1.0f : powf(AQ[node],AQ_BETA)))
#endif


static void build_node_domcost_heap_comb(){
  clearHeap(Node_Heap);
  for_each_undomed_node(node){
    assert(!selected(node));
    assert(!domed(node));
    float cost=HEUR(node);
    insertHeap(Node_Heap,node,cost);
  }
#ifdef CHECK
   check_heap(Node_Heap);
#endif
}



static void aq_init();

static void ___initialize(){

  //initialize_km_min(NB_NODE);
  //allocate memory
  CFG=(int *)malloc((NB_NODE+1)*sizeof(int));
  LOC=(int *)malloc((NB_NODE+1)*sizeof(int));
  UBC=(int *)malloc((NB_NODE+1)*sizeof(int));

  Node_Score   = (float *)malloc((NB_NODE+1)*sizeof(float));
  Touch_Deltas = (int **)malloc((NB_NODE+1)*sizeof(int *));

 

  // DomSum      = (WeightSum *)malloc((NB_NODE+1)*sizeof(WeightSum));
  // DomedNumber = (int *)malloc((NB_NODE+1)*sizeof(int));
  // DomedReason = (int *)malloc((NB_NODE+1)*sizeof(int));
  MinNeibor   = (int *)malloc((NB_NODE+1)*sizeof(int));
  MinNeiborBak= (int *)malloc((NB_NODE+1)*sizeof(int));
  Loss        = (int *)malloc((NB_NODE+1)*sizeof(int));
  Subs        = (int *)malloc((NB_NODE+1)*sizeof(int));
  Loss_Bak    = (int *)malloc((NB_NODE+1)*sizeof(int));
  Subs_Bak    = (int *)malloc((NB_NODE+1)*sizeof(int));
  Beta        = (float *)malloc((NB_NODE+1)*sizeof(float));
  PairList    = (LBPair *)malloc((NB_NODE+1)*sizeof(LBPair));
  PairIndex   = (int *)malloc((NB_NODE+1)*sizeof(int));
  aq_init();
         
  BRAIDX=(int *)malloc((NB_NODE+1)*sizeof(int));
  UNDIDX=(int *)malloc((NB_NODE+1)*sizeof(int));
  STATUS=(VSTATUS *)calloc((NB_NODE+1),sizeof(VSTATUS));
 
  PID=(PSTATUS *)calloc((NB_NODE+1),sizeof(PSTATUS));

  // initialize stack
   
  // create_stack(FIX_STK,VEC_INT,int,2*NB_NODE+1);
  //create_stack(BRA_STK,VEC_INT,int,2*NB_NODE+1);
  create_stack(UNIT_STK,VEC_INT,int,NB_NODE+1);
  //create_stack(PART_STK,VEC_INT,int,NB_NODE+1);
  create_stack(VEC_SOLUTION,VEC_INT,int,NB_NODE+1);
  create_stack(VEC_PARTIAL,VEC_INT,int,NB_NODE+1);

  Node_Heap=(MaxHeap *)malloc(sizeof(MaxHeap));
  
  initHeap(Node_Heap,NB_NODE,node_cmp_for_MaxHeap);

  
  memset(STATUS,0,(NB_NODE+1)*sizeof(VSTATUS));
  memset(PID,0,(NB_NODE+1)*sizeof(PSTATUS));

  for(int node=1;node<=NB_NODE;node++){
    value(node)=V_UNDEF;
    // DomedNumber[node]=0;
    // DomedReason[node]=0;
    MinNeibor[node]=0;
    // DomSum[node]=0;
    Loss[node]=0;
    Subs[node]=1;
    Loss_Bak[node]=0;
    Subs_Bak[node]=1;
    Beta[node]=1.0;
    PairIndex[node]=NB_NODE;
  }
}


static void init_state_ubc_domcost_enable(int v_State[],int v_Cost[]){
  ACTIVE_NODE=0;
  ACTIVE_EDGE=0;
  ___initialize();

  WeightSum UB=0; 
 for(int v=1;v<=NB_NODE;v++){
   Node_Weight[v]=v_Cost[v];
   UB+=v_Cost[v];
   if(v_State[v] == STATE::Fixed || v_State[v] > 10)
     fixed(v)=1;
   else if(v_State[v] == STATE::Deleted)
     deleted(v)=1;
 }
 BEST_UPPER_BOUND=INIT_UPPER_BOUND=UB;
  for(int node=1;node<=NB_NODE;node++){   
    if(deleted(node))
      continue;

    int *ptr=Node_Neibors[node],count=0;
    for_each_neighbor(node,neibor){
      if(!deleted(neibor)){
	*ptr++=neibor;count++;
      }
    }
    *ptr=NONE;
    Node_Degree[node]=count;

    ACTIVE_NODE++;
     
    int cost=Node_Weight[node];
    int min_neibor=node;
   
    // UBC[node]=0;
    // if(!branched(node))
    UBC[node]=1;
    for_each_neighbor(node,neibor){
      UBC[node]++;
      if(Node_Weight[neibor]<cost){
	cost=Node_Weight[neibor];
	min_neibor=neibor;
      }
    }
    DomCost[node]=cost;
    MinNeiborBak[node]=MinNeibor[node]=min_neibor;
    // assert(min_neibor);
    ACTIVE_EDGE+=Node_Degree[node];
  }
  INIT_TIME=get_utime();
}


void build_problem_config(){
  int j=0,fixed_count=0;
  // USED(FIX_STK)=0;
  USED(UNIT_STK)=0;
  USED(VEC_PARTIAL)=0;
  for(int node=1;node<=NB_NODE;node++){
    if(deleted(node))
      continue;
    CFG[j]=node;
    LOC[node]=j++;
    clr_value(node);
    clr_domed_status(node);
    clr_involved_status(node);
     
    if(fixed(node)){
      fixed_count++;
      push_back(VEC_PARTIAL,int,node);
    }
  }
  CFG[j]=NONE;
  SUB_PROBLEM_SIZE=j;
}


void init_for_search(){

  CUR_LEVEL=0;
  CUR_BOUND=0;
  // CUR_BRA_IDX=0;
  CUR_UND_IDX=0;
  //USED(BRA_STK)=0;
  USED(UNIT_STK)=0;
  CUR_LEVEL_UND_IDX=0;
  FIRST_LOWER_BOUND=0;
  // push_back(BRA_STK,int,NONE);

  for(int i=0,fnode;i<USED(VEC_PARTIAL);i++){
    fnode=ITEM(VEC_PARTIAL,i);

    assert(fixed(fnode));
    assert(value(fnode)==V_UNDEF);
    value(fnode)=V_TRUE;
    CUR_BOUND+=Node_Weight[fnode];
    
    if(!domed(fnode)){
      set_domed_status(fnode);
      swap_cfg(CFG[CUR_UND_IDX],fnode);
      CUR_UND_IDX++;
    }
   
    for_each_neighbor(fnode,neibor){
      if(!domed(neibor)){
	int first=CFG[CUR_UND_IDX];
	if(first!=neibor)
	  swap_cfg(first,neibor);
	set_domed_status(neibor);
	CUR_UND_IDX++;
      }
    }   
  }
 
  NB_FIXED=USED(VEC_PARTIAL);
  USED(UNIT_STK)=0;
  // printf(">>IBM: NB_FIXED %d, NB_UNDOMED %d \n",NB_FIXED,SUB_PROBLEM_SIZE-CUR_UND_IDX);
  if(SUB_PROBLEM_SIZE-CUR_UND_IDX<10000)
    MaxIteration=500;
  else if(SUB_PROBLEM_SIZE-CUR_UND_IDX<100000)
    MaxIteration=50;
  else if (SUB_PROBLEM_SIZE-CUR_UND_IDX<1000000)
    MaxIteration=10;
  else
    MaxIteration=2; 
  // printf(">>IBM: Using MaxIteration  %d \n",MaxIteration);
}



static int unimproved=0;

/*============================================================
 *  AntQO v1 函数实现
 *
 *  调用关系:
 *    compute_bounds()
 *      └── 每次迭代的蚂蚁循环中:
 *            ├── aq_build_ordering()     构造一个排序
 *            ├── aq_count_violated()     计算 violated 数
 *            └── aq_compute_score()      打分
 *          蚂蚁循环结束后:
 *            └── aq_update_values()      更新 AQ
 *
 *    ibmwds_init_bounds()
 *      └── aq_check_restart()           停滞重启检查
 *
 *    ___initialize() / init_for_search()
 *      └── aq_init()                    内存分配与初始化
 *============================================================*/

/**
 * 分配 AQ 数组内存并初始化为 τ₀
 * 调用时机：在 ___initialize() 中，Beta 分配之后
 */
static void aq_init(){
  AQ = (float *)malloc((NB_NODE+1)*sizeof(float));
  BestAnt_PairList = (LBPair *)malloc((NB_NODE+1)*sizeof(LBPair));
  for(int v=1; v<=NB_NODE; v++){
    AQ[v] = AQ_TAU0;
  }
}

/**
 * 带 q0 机制的排序构造（替代 compute_bounds 中的 while 循环）
 *
 * 返回本次构造的 lb 值。PairList/PairIndex/PairLength 在调用过程中被填充。
 *
 * 选择逻辑：
 *   - 以 q0 概率：取堆顶（利用，HEUR' 最高）
 *   - 以 1-q0 概率：对所有候选按 HEUR' 概率分布随机选（探索）
 */
static WeightSum aq_build_ordering(int *out_pair_length){
  int index = -1;
  WeightSum lb = 0;

  build_node_domcost_heap_comb();

  while(1){
    int best_node = 0, select_node;
    float max_cost = 0;

    float r = (float)rand() / RAND_MAX;
    float effective_q0 = (AQ_PHASE == 1) ? 1.0f : AQ_Q0;
    #ifndef EXP9_DISABLE_LB_FIRST_ANT
    if(AQ_PHASE == 2 && USE_ADVANCED && BEST_UPPER_BOUND > BEST_LOWER_BOUND){
      /*
       * exp-9: generic stagnation recovery. When LB construction keeps
       * returning the same bound, reduce greedy pressure and sample a broader
       * ordering space. This uses only runtime search state, not benchmark IDs.
       */
      if(AQ_Stagnation >= 3 || (MaxIteration > 0 && unimproved >= MaxIteration / 2)){
        effective_q0 = 0.35f;
      }else if(FIRST_GAP >= 0.25 && effective_q0 > 0.65f){
        effective_q0 = 0.65f;
      }
    }
    #endif
    if(r < effective_q0){
      /* --- 利用：原始堆顶选择（含延迟验证）--- */
      float keyval = 0;
      do{
        HeapNode temp = removeTop(Node_Heap);
        best_node = temp.key;
        if(best_node && domed(best_node)){ best_node = -1; continue; }
        max_cost = DeltaCost[best_node];
        if(best_node) keyval = HEUR(best_node);
        if(best_node && temp.value && temp.value != keyval){
          insertHeap(Node_Heap, best_node, keyval);
          best_node = -1;
        }
      }while(best_node < 0);
    } else {
      /* --- 探索：按 HEUR' 概率分布随机选 --- */
      double sum = 0.0;
      for_each_undomed_node(node){
        if(!domed(node) && !selected(node) && DeltaCost[node] > 0)
          sum += HEUR(node);
      }
      if(sum > 0){
        double pick = ((double)rand() / RAND_MAX) * sum;
        double acc = 0.0;
        for_each_undomed_node(node){
          if(!domed(node) && !selected(node) && DeltaCost[node] > 0){
            acc += HEUR(node);
            if(acc >= pick){ best_node = node; break; }
          }
        }
        if(best_node) max_cost = DeltaCost[best_node];
      }
      /* 探索选不出来时（全零），走堆排空逻辑：best_node 保持 0 */
    }

    if(!best_node) break;

    lb += max_cost;
    index++;

    select_node = MinNeibor[best_node];

    PairIndex[best_node] = index;
    PairList[index].target   = best_node;
    PairList[index].select   = select_node;
    PairList[index].delta    = max_cost;
    PairList[index].replaced = 0;

    set_selected_status(best_node);
    set_domed_status(select_node);
    for_each_neighbor(select_node, neibor){
      set_domed_status(neibor);
    }

    if(!max_cost) continue;

    if(!branched(best_node))
      update_node_delta(best_node, max_cost);
    for_each_neighbor(best_node, neibor){
      if(!branched(neibor))
        update_node_delta(neibor, max_cost);
    }
  }

  *out_pair_length = index + 1;
  return lb;
}

/**
 * 轻量计算 violated 顶点数
 *
 * 镜像 compute_loss_and_upper_bound() 的第一个循环逻辑，
 * 但不修改 Loss/Subs/domed_status，只计算 replaced 计数。
 *
 * 前置条件：PairList/PairIndex/selected() 已由当前蚂蚁的排序构造设置好
 * 后置条件：PairList[i].replaced 被重置为 0
 */
static int aq_count_violated(int pair_length){
  for(int i=pair_length-1; i>=0; i--){
    if(PairList[i].replaced > 0)
      continue;
    int sn = PairList[i].select;
    if(selected(sn)){
      int j = PairIndex[sn];
      if(j < i) PairList[j].replaced++;
    }
    for_each_neighbor(sn, nb){
      if(selected(nb)){
        int j = PairIndex[nb];
        if(j < i) PairList[j].replaced++;
      }
    }
  }
  int count = 0;
  for(int i=0; i<pair_length; i++){
    if(PairList[i].replaced > 0) count++;
    PairList[i].replaced = 0;
  }
  return count;
}

/**
 * 复合评分公式
 * Score(O_k) = bound_k * (1 - λ * n_violated / m_k)
 */
static double aq_compute_score(WeightSum bound, int n_violated, int pair_length){
  if(pair_length == 0) return 0.0;
  return (double)bound * (1.0 - AQ_LAMBDA * (double)n_violated / pair_length);
}

/**
 * AQ 值更新（每次迭代结束后，对最优蚁的结果执行）
 *
 * 步骤：
 *   1. 全局蒸发：AQ(v) *= (1 - ρ)
 *   2. 最优蚁强化：对排序中的顶点 AQ(v) += ΔAQ
 *      - 非 violated: ΔAQ = Score / W_total
 *      - violated:    ΔAQ = Score / W_total * (1 - λ)
 *   3. Tight bonus: 若 OPTIMAL，额外 ΔAQ *= 3
 *   4. 钳位到 [τ_min, τ_max]
 *
 * is_tight: 本次迭代是否达到 tight（OPTIMAL 标志）
 */
static void aq_update_values(double best_score, int pair_length, int is_tight){
  double w_total = (double)INIT_UPPER_BOUND;
  if(w_total <= 0) return;
  double delta_aq = best_score / w_total;
  if(is_tight) delta_aq *= 3.0;

  /* 1. 全局蒸发 */
  for_each_undomed_node(v){
    AQ[v] *= (1.0f - AQ_RHO);
  }

  /* 2. 最优蚁强化（区分 violated / 非 violated） */
  for(int i=0; i<pair_length; i++){
    int target = PairList[i].target;
    float reinforce = (float)delta_aq;
    if(PairList[i].replaced > 0)
      reinforce *= (1.0f - AQ_LAMBDA);
    AQ[target] += reinforce;
  }

  /* 3. 钳位 */
  for_each_undomed_node(v){
    if(AQ[v] < AQ_TAU_MIN) AQ[v] = AQ_TAU_MIN;
    if(AQ[v] > AQ_TAU_MAX) AQ[v] = AQ_TAU_MAX;
  }
}

/**
 * AQ 停滞重启检查
 *
 * 在 ibmwds_init_bounds 中、compute_bounds 之前调用。
 * 如果连续多个 round lb 无改善（AQ_Stagnation >= threshold），
 * 将 AQ 重置为 τ₀。
 */
static void aq_check_restart(int lb_improved){
  if(USE_ADVANCED){
    if(lb_improved){
      AQ_RHO = AQ_RHO * 0.9f;
      if(AQ_RHO < 0.02f) AQ_RHO = 0.02f;
    } else {
      AQ_RHO = AQ_RHO * 1.1f;
      if(AQ_RHO > 0.15f) AQ_RHO = 0.15f;
    }
  }
  if(AQ_Stagnation >= AQ_RESTART_THRESHOLD){
    if(USE_ADVANCED){
      for_each_undomed_node(v){
        AQ[v] = AQ[v] * 0.3f + AQ_TAU0 * 0.7f;
      }
      AQ_RHO = 0.05f;
    } else {
      for_each_undomed_node(v){
        AQ[v] = AQ_TAU0;
      }
    }
    AQ_Stagnation = 0;
  }
}

static void aq_ub_feedback(int *sol_vertices, int sol_size, long long ub_value){
  if(!AQ_ENABLED || sol_size <= 0 || INIT_UPPER_BOUND <= 0) return;
  float bonus = (float)((double)(INIT_UPPER_BOUND - ub_value) / INIT_UPPER_BOUND) * 0.5f;
  if(bonus <= 0) return;
  for(int i = 0; i < sol_size; i++){
    int v = sol_vertices[i];
    if(v >= 1 && v <= NB_NODE){
      AQ[v] += bonus;
      if(AQ[v] > AQ_TAU_MAX) AQ[v] = AQ_TAU_MAX;
    }
  }
}


static inline int compute_bounds(int k,double cutoff){
  #ifdef RESTART
  memset(Loss,0,(NB_NODE+1)*sizeof(int));
  for(int node=1;node<=NB_NODE;node++){
      Subs[node]=1;
  }
  #else
  if(k>0){
  memcpy(Loss, Loss_Bak,(NB_NODE+1)*sizeof(int));
  memcpy(Subs, Subs_Bak,(NB_NODE+1)*sizeof(int));
  }
  #endif  
  BEST_UPPER_BOUND=INIT_UPPER_BOUND;
  BEST_LOWER_BOUND=0;
  double _start=get_utime();
  int inner_iter = 0;
  do{

    int cur_K;
    if(AQ_ENABLED){
      AQ_PHASE = 2;
      cur_K = AQ_NUM_ANTS;
    } else {
      AQ_PHASE = 1;
      cur_K = 1;
    }
    inner_iter++;

    /*--- 多蚂蚁循环：K 只蚂蚁各自构造排序 ---*/
    BestAnt_Score = -1.0;
    BestAnt_LB = 0;
    BestAnt_PairLength = 0;

    for(int ant=0; ant<cur_K; ant++){
      memcpy(DeltaCost, DomCost,(NB_NODE+1)*sizeof(unsigned));
      memcpy(Node_Delta, Node_Weight,(NB_NODE+1)*sizeof(unsigned));
      memcpy(MinNeibor, MinNeiborBak,(NB_NODE+1)*sizeof(int));
      for_each_undomed_node(node){
        clr_domed_status(node);
        clr_selected_status(node);
      }

      int ant_pair_length;
      WeightSum ant_lb = aq_build_ordering(&ant_pair_length);
      WeightSum ant_bound = ant_lb + CUR_BOUND;

      int ant_violated = aq_count_violated(ant_pair_length);
      double ant_score = aq_compute_score(ant_bound, ant_violated, ant_pair_length);

      /*
       * LB construction should first maximize the valid lower bound. The
       * violation-aware score remains useful, but only as a tie breaker among
       * orderings with the same bound.
       */
      #ifdef EXP9_DISABLE_LB_FIRST_ANT
      if(ant_score > BestAnt_Score){
      #else
      if(ant_bound > BestAnt_LB ||
         (ant_bound == BestAnt_LB && ant_score > BestAnt_Score)){
      #endif
        BestAnt_Score = ant_score;
        BestAnt_LB = ant_bound;
        BestAnt_PairLength = ant_pair_length;
        memcpy(BestAnt_PairList, PairList, ant_pair_length*sizeof(LBPair));
      }
    }

    /*--- 恢复最优蚁的结果到全局数组 ---*/
    memcpy(PairList, BestAnt_PairList, BestAnt_PairLength*sizeof(LBPair));
    PairLength = BestAnt_PairLength;
    for_each_undomed_node(node){
      clr_domed_status(node);
      clr_selected_status(node);
      PairIndex[node] = NB_NODE;
    }
    for(int i=0; i<PairLength; i++){
      PairIndex[PairList[i].target] = i;
      set_selected_status(PairList[i].target);
    }

    /*--- 评估（与原始逻辑一致，只对最优蚁执行）---*/
    unimproved++;
    WeightSum bound = BestAnt_LB;

    if(bound>BEST_LOWER_BOUND){
      unimproved=0;
      BEST_LOWER_BOUND=bound;
      if(BEST_LOWER_BOUND>=BEST_BEST_LOWER_BOUND){
	BEST_BEST_LOWER_BOUND=BEST_LOWER_BOUND;
	memcpy(Loss_Bak, Loss,(NB_NODE+1)*sizeof(int));
	memcpy(Subs_Bak, Subs,(NB_NODE+1)*sizeof(int));
      }
    }

    if(compute_loss_and_upper_bound(bound)){
      break;
    }

    /*--- AQ 学习 ---*/
    if(AQ_PHASE == 2)
      aq_update_values(BestAnt_Score, PairLength, OPTIMAL);
    else if(USE_ADVANCED) {
      double w_total = (double)INIT_UPPER_BOUND;
      if(w_total > 0 && PairLength > 0){
        double weak_delta = (double)bound / w_total * 0.03;
        for(int pi = 0; pi < PairLength; pi++){
          int v = PairList[pi].target;
          AQ[v] += (float)weak_delta;
          if(AQ[v] > AQ_TAU_MAX) AQ[v] = AQ_TAU_MAX;
        }
      }
    }

#ifdef AQ_DIAG
    {
      float aq_min=AQ_TAU_MAX, aq_max=AQ_TAU_MIN;
      double aq_sum=0; int aq_cnt=0;
      int diag_viol=0;
      for_each_undomed_node(v){
        if(AQ[v]<aq_min) aq_min=AQ[v];
        if(AQ[v]>aq_max) aq_max=AQ[v];
        aq_sum+=AQ[v]; aq_cnt++;
      }
      for(int i=0;i<PairLength;i++)
        if(PairList[i].replaced>0) diag_viol++;
      printf("  [AQ] min=%.4f avg=%.4f max=%.4f  score=%.1f viol=%d/%d\n",
             aq_min, aq_sum/aq_cnt, aq_max, BestAnt_Score,
             diag_viol, PairLength);
    }
#endif

    if((cutoff && get_utime()-_start>=cutoff) || (getTimeElapsed()>time_Cutoff))
      break;
  }while(unimproved<MaxIteration);
 
  return 1;
}

int ibmwds_init_bounds(int k,double *timeout){
  double cutoff=0;
  INIT_TIME=get_utime();
  if(k==0){
    build_problem_config();
    init_for_search();
  }else{
    static WeightSum prev_best_lb = 0;
    int lb_improved = (BEST_BEST_LOWER_BOUND > prev_best_lb);
    if(lb_improved){
      AQ_Stagnation = 0;
      prev_best_lb = BEST_BEST_LOWER_BOUND;
    } else {
      AQ_Stagnation++;
    }
    aq_check_restart(lb_improved);

    /* 自适应 γ：停滞时加大 Beta 增长幅度 */
    double adaptive_alpha = ALPHA;
    if(AQ_Stagnation > 3)
      adaptive_alpha = ALPHA * 1.5;

    for(int i=0,node;i<USED(UNIT_STK);i++){
        node=ITEM(UNIT_STK,i);
	Beta[node]*=adaptive_alpha;
    }

     if(k==1){
      for(int i=1;;i++){
        int k=i*ALPHA;
        if(i+1<k){
	  MaxIteration=i;
	  break;
	}
      }
    }else{
#ifndef NDYN
      MaxIteration=MaxIteration*ALPHA;
      *timeout=(*timeout)*ALPHA;
      if(ALPHA>1.05){
	ALPHA=(ALPHA)/(1+0.02*ALPHA);
#endif
      }
    }
    printf("ALPHA %.4lf MaxIteration %d  TIMEOUT %lf\n",ALPHA,MaxIteration,*timeout);
    cutoff=*timeout;
  }
  compute_bounds(k,cutoff);

  #ifndef EXP9_DISABLE_EXACT_CHECK
  WeightSum exact_small_lb = compute_exact_small_weighted_dom_lb();
  if(exact_small_lb > BEST_LOWER_BOUND){
    BEST_LOWER_BOUND = exact_small_lb;
    if(BEST_LOWER_BOUND > BEST_BEST_LOWER_BOUND)
      BEST_BEST_LOWER_BOUND = BEST_LOWER_BOUND;
  }
  if(exact_small_dom_ub > 0 && exact_small_dom_ub < BEST_UPPER_BOUND){
    BEST_UPPER_BOUND = exact_small_dom_ub;
    USED(VEC_SOLUTION) = 0;
    if(exact_small_dom_solution_size > 0){
      for(int i = 0; i < exact_small_dom_solution_size; i++)
        push_back(VEC_SOLUTION, int, exact_small_dom_solution[i]);
    }else{
    if(exact_small_dom_node1)
      push_back(VEC_SOLUTION, int, exact_small_dom_node1);
    if(exact_small_dom_node2)
      push_back(VEC_SOLUTION, int, exact_small_dom_node2);
    }
  }
  if(BEST_UPPER_BOUND == BEST_LOWER_BOUND)
    OPTIMAL = 1;
  #endif

  if(!FIRST_LOWER_BOUND){
    FIRST_LOWER_BOUND=BEST_LOWER_BOUND;
  }

  if(BEST_LOWER_BOUND>BEST_BEST_LOWER_BOUND)
    BEST_BEST_LOWER_BOUND=BEST_LOWER_BOUND;

  if(!FIRST_UPPER_BOUND)
    FIRST_UPPER_BOUND=BEST_UPPER_BOUND;

  if(FIRST_GAP==0){
    FIRST_GAP= (FIRST_UPPER_BOUND-FIRST_LOWER_BOUND)/(double)FIRST_LOWER_BOUND;
    printf("First Gap  %lf\n",FIRST_GAP);
  }
  *timeout=get_utime()-INIT_TIME;
  printf("%3d %10lld %10lld %10lld %11.4lf", k+1, BEST_LOWER_BOUND, BEST_BEST_LOWER_BOUND, BEST_UPPER_BOUND,*timeout); 

  return OPTIMAL;
}


