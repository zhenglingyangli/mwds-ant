#include "util_heap.h"
#include "util_vector.h"
#include <sys/resource.h>
#define TRUE 1
#define FALSE 0
#define NONE 0

#define WeightSum long long

#define for_each_vertex(node) for(int node=1;node<=NB_NODE;node++)
#define for_each_neighbor(__vertex,__neibor)  for(int * __ptr=Node_Neibors[__vertex],__neibor=*__ptr;__neibor!=NONE;__neibor=*(++__ptr))
#define for_each_undomed_node(node)   for(int __i=SUB_PROBLEM_SIZE-1,node=CFG[__i];__i>=CUR_UND_IDX;node=CFG[--__i])

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

#define marked(node) (PID[node].marked)
#define set_marked_status(node) (PID[node].marked=1)
#define clr_marked_status(node) (PID[node].marked=0)

#define touched(node) (PID[node].touched)
#define set_touched_status(node) (PID[node].touched=1)
#define clr_touched_status(node) (PID[node].touched=0)

#define selected(node) (PID[node].selected)
#define set_selected_status(node) (PID[node].selected=1)
#define clr_selected_status(node) (PID[node].selected=0)
  
#define involved(node) (PID[node].involved)
#define set_involved_status(node) (PID[node].involved=1)
#define clr_involved_status(node) (PID[node].involved=0)

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
 unsigned char isno:4;
}PSTATUS;


extern double read_time,time_limit;

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
static int  *Loss;
static int  *Subs;
static float *Beta;

static unsigned *Node_Degree;

static int NB_NODE,NB_EDGE, Max_Degree = 0, Max_Degree_Node,SUB_PROBLEM_SIZE;
static int FORMAT = 1,  NB_NODE_O,  NB_EDGE_O;
static double READ_TIME, INIT_TIME, SEARCH_TIME;
static int INIT_BRANCHING_NODE=0;
static WeightSum INIT_UPPER_BOUND=0;
static unsigned long long NB_TREE=0,NB_CUT=0;

static int * CFG;
static int * LOC;
static int * UBC;



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

static int TIME_OUT, CUT_OFF=0;
static double BEST_SOL_TIME;
static char instance[1024]={'\0'};
//static VEC_INT *iSET[MAXIS+1];
//static int iSET_Counter[MAXIS+1];
//static int iSET_Status[MAXIS+1];
//static int iSET_Insert[MAXIS+1];
//static WeightSum iSET_Weight[MAXIS+1];
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
static double FIRST_GAP=0.0;
static double ALPHA=1.50;

static float *AQ; //信息素浓度
static float AQ_TAU0     = 1.0f;
static float AQ_RHO      = 0.05f;//蒸发率
static float AQ_Q0       = 0.9f;//贪心 exploitation
static float AQ_TAU_MIN  = 0.01f;//最小信息素浓度
static float AQ_TAU_MAX  = 20.0f;
static float AQ_LAMBDA   = 0.3f;//惩罚系数
static float AQ_BETA     = 3.5f;//信息素的影响指数
static int   AQ_NUM_ANTS = 5;//蚂蚁数量

static int   AQ_PHASE   = 1;
static int   AQ_ENABLED = 0;
static int   AQ_ACTIVE  = 0;
static int   AQ_TOUCH_UB = 0;
static int   USE_ADVANCED = 0;//当图的节点数 >= 800 时设为 1，大图，开启自适应蒸发率、停滞重启、局部搜索中多删点扰动等

static LBPair *BestAnt_PairList;
static int     BestAnt_PairLength;

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

static int _read_graph_wclq_format(int nb_node,int nb_edge,int v_Deg[], int ** v_Adj,int v_Cost[]) {

        int max_weight=0;
        
	NB_NODE = nb_node;
	NB_EDGE = nb_edge;
	
	printf(">>IBM: |V|=%d |E|=%d\n", NB_NODE,nb_edge);

	Node_Degree=(unsigned *) malloc((NB_NODE + 1) * sizeof(unsigned));
	Node_Weight=(unsigned *) malloc((NB_NODE + 1) * sizeof(unsigned));
	Node_Delta=(unsigned *) malloc((NB_NODE + 1) * sizeof(unsigned));
	DomCost=(unsigned *) malloc((NB_NODE + 1) * sizeof(unsigned));
	DeltaCost=(unsigned *) malloc((NB_NODE + 1) * sizeof(unsigned));
	//ZeroTouch=(int *) malloc((NB_NODE + 1) * sizeof(int));
	Node_Neibors = (int **) malloc((NB_NODE + 1) * sizeof(int *));
	Max_Degree = 0;
	
        for (int v = 1; v <= NB_NODE; v++) {
	  Node_Degree[v]=v_Deg[v-1];
	  Node_Weight[v]=v_Cost[v-1];
	  if (Node_Degree[v] > Max_Degree)
	    Max_Degree = Node_Degree[v];
	  if (Node_Weight[v] > max_weight)
	    max_weight = Node_Weight[v];
	}

	allcoate_memory_for_adjacency_list(NB_NODE, nb_edge, 0);
	
	for (int v = 1; v <= NB_NODE; v++) {
	  for(int i=0;i<v_Deg[v-1];i++){
	    Node_Neibors[v][i] = v_Adj[v-1][i]+1;
	  }
	  Node_Neibors[v][v_Deg[v-1]]=NONE;
	}
	printf(">>IBM: The maximum node weight is %d\n",max_weight);
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
static int *SubGraph_size,NB_DCC=0,*InDcc,NB_cut=0;
static double REDUCE_TIME=0;



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
   if(AQ_ENABLED && AQ_ACTIVE && AQ_TOUCH_UB && AQ_PHASE == 2)
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
    
  if((rep_flag==0 && loss_sum==0)
     || (BEST_UPPER_BOUND==BEST_LOWER_BOUND))
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
#define HEUR(node) ((Beta[node]*DeltaCost[node])/(term1(node)*(term2(node)+term3(node)))*((AQ_ENABLED && AQ_ACTIVE && AQ_PHASE==2) ? powf(AQ[node],AQ_BETA) : 1.0f))
#endif


static void build_node_domcost_heap_comb(){
  clearHeap(Node_Heap);
  for_each_undomed_node(node){
    // assert(!selected(node));
    //assert(!domed(node));
    float cost=HEUR(node);
    insertHeap(Node_Heap,node,cost);
  }
#ifdef CHECK
   check_heap(Node_Heap);
#endif
}



static void ___initialize(){

  
  CFG=(int *)malloc((NB_NODE+1)*sizeof(int));
  LOC=(int *)malloc((NB_NODE+1)*sizeof(int));
  UBC=(int *)malloc((NB_NODE+1)*sizeof(int));

  Node_Score   = (float *)malloc((NB_NODE+1)*sizeof(float));
 
  MinNeibor   = (int *)malloc((NB_NODE+1)*sizeof(int));
  MinNeiborBak= (int *)malloc((NB_NODE+1)*sizeof(int));
  Loss        = (int *)malloc((NB_NODE+1)*sizeof(int));
  Subs        = (int *)malloc((NB_NODE+1)*sizeof(int));
  Beta        = (float *)malloc((NB_NODE+1)*sizeof(float));
  PairList    = (LBPair *)malloc((NB_NODE+1)*sizeof(LBPair));
  PairIndex   = (int *)malloc((NB_NODE+1)*sizeof(int));
  AQ          = (float *)malloc((NB_NODE+1)*sizeof(float));
  BestAnt_PairList = (LBPair *)malloc((NB_NODE+1)*sizeof(LBPair));
        
  UNDIDX=(int *)malloc((NB_NODE+1)*sizeof(int));
  STATUS=(VSTATUS *)calloc((NB_NODE+1),sizeof(VSTATUS));
 
  PID=(PSTATUS *)calloc((NB_NODE+1),sizeof(PSTATUS));

  // initialize stack
   
  create_stack(UNIT_STK,VEC_INT,int,NB_NODE+1);
  create_stack(VEC_SOLUTION,VEC_INT,int,NB_NODE+1);
  create_stack(VEC_PARTIAL,VEC_INT,int,NB_NODE+1);

  Node_Heap=(MaxHeap *)malloc(sizeof(MaxHeap));
  
  initHeap(Node_Heap,NB_NODE,node_cmp_for_MaxHeap);

  
  memset(STATUS,0,(NB_NODE+1)*sizeof(VSTATUS));
  memset(PID,0,(NB_NODE+1)*sizeof(PSTATUS));

  for(int node=1;node<=NB_NODE;node++){
    value(node)=V_UNDEF;
    // DomedNumber[node]=0;
    //DomedReason[node]=0;
    MinNeibor[node]=0;
    // DomSum[node]=0;
    Loss[node]=0;
    Subs[node]=1;
    Beta[node]=1.0;
    PairIndex[node]=NB_NODE;
    AQ[node]=AQ_TAU0;
  }
}


static void init_state_ubc_domcost_enable(int v_State[]){
 
  ___initialize();

  WeightSum UB=0; 
 for(int v=1;v<=NB_NODE;v++){
   UB+=Node_Weight[v];
   if(v_State[v-1] == 1)
     fixed(v)=1;
   else if(v_State[v-1] == 2)
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
     
    int cost=Node_Weight[node];
    int min_neibor=node;
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
/*
static void update_cfg(){
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
}
*/
void init_for_search(){

  CUR_LEVEL=0;
  CUR_BOUND=0;
  CUR_UND_IDX=0;
  USED(UNIT_STK)=0;
  FIRST_LOWER_BOUND=0;

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

/**
 * AQ 排序构造：带伪随机比例选择
 */
static WeightSum aq_build_ordering(int *out_pair_length){
  int index = -1;
  WeightSum lb = 0;

  build_node_domcost_heap_comb();

  while(1){
    //每次循环选一个节点加入构造序列
    int best_node = 0, select_node;//选中的和其支配的
    float max_cost = 0;

    float r = (float)rand() / RAND_MAX;//[0,1)
    float effective_q0 = (AQ_PHASE == 1) ? 1.0f : AQ_Q0;
    if(r < effective_q0){ //exploitation利用,同v0
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
    } else { //exploration探索，轮盘赌，每个节点被选中的概率与它的 HEUR 值成正比
      double sum = 0.0;
      for_each_undomed_node(node){
        if(!domed(node) && !selected(node) && DeltaCost[node] > 0)
          sum += HEUR(node);
      }
      if(sum > 0){
        double pick = ((double)rand() / RAND_MAX) * sum;//[0, sum)
        double acc = 0.0;
        for_each_undomed_node(node){
          if(!domed(node) && !selected(node) && DeltaCost[node] > 0){
            acc += HEUR(node);
            if(acc >= pick){ best_node = node; break; }
          }
        }
      }
      if(best_node) max_cost = DeltaCost[best_node];
    }

    if(!best_node) break;

    lb += max_cost;
    index++;
    select_node = MinNeibor[best_node];

    PairIndex[best_node] = index;
    PairList[index].target  = best_node;
    PairList[index].select  = select_node;
    PairList[index].delta   = max_cost;
    PairList[index].replaced= 0;

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

static int aq_count_violated(int pair_length){
  for(int i = pair_length-1; i >= 0; i--){
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
  for(int i = 0; i < pair_length; i++){
    if(PairList[i].replaced > 0) count++;
    PairList[i].replaced = 0;
  }
  return count;
}

static double aq_compute_score(WeightSum bound, int n_violated, int pair_length){
  if(pair_length == 0) return 0.0;
  return (double)bound * (1.0 - AQ_LAMBDA * (double)n_violated / pair_length);
}

static void aq_update_values(double best_score, int pair_length, int is_tight){
  double w_total = (double)INIT_UPPER_BOUND;
  if(w_total <= 0) return;
  double delta_aq = best_score / w_total;// 本轮最优蚂蚁的综合得分/初始上界值（所有节点权重之和）。

  for(int v = 1; v <= NB_NODE; v++){
    AQ[v] *= (1.0f - AQ_RHO);//蒸发
  }
  for(int i = 0; i < pair_length; i++){
    int v = BestAnt_PairList[i].target;
    float reinforce = (float)delta_aq;
    if(BestAnt_PairList[i].replaced)
      reinforce *= (1.0f - AQ_LAMBDA);
    AQ[v] += reinforce;//强化
  }
  for(int v = 1; v <= NB_NODE; v++){ //放在区间内
    if(AQ[v] < AQ_TAU_MIN) AQ[v] = AQ_TAU_MIN;
    if(AQ[v] > AQ_TAU_MAX) AQ[v] = AQ_TAU_MAX;
  }
}

static int AQ_Stagnation = 0;
static WeightSum AQ_Last_Best_LB = 0;

static void aq_check_restart(){
  int lb_improved = (BEST_BEST_LOWER_BOUND > AQ_Last_Best_LB);
  if(lb_improved){
    AQ_Last_Best_LB = BEST_BEST_LOWER_BOUND;
    AQ_Stagnation = 0;
  } else {
    AQ_Stagnation++;//停滞
  }
  if(USE_ADVANCED){//蒸发率会随是否进步而自适应变化
    if(lb_improved){
      AQ_RHO = AQ_RHO * 0.9f;
      if(AQ_RHO < 0.02f) AQ_RHO = 0.02f;
    } else {
      AQ_RHO = AQ_RHO * 1.1f;
      if(AQ_RHO > 0.15f) AQ_RHO = 0.15f;
    }
  }
  if(AQ_Stagnation >= 10){//停滞太久就做重启
    if(USE_ADVANCED){ //图模式下做 70% 重置 + 30% 保留
      for(int v = 1; v <= NB_NODE; v++)
        AQ[v] = AQ[v] * 0.3f + AQ_TAU0 * 0.7f;
      AQ_RHO = 0.05f;
    } else {
      for(int v = 1; v <= NB_NODE; v++)
        AQ[v] = AQ_TAU0;
    }
    AQ_Stagnation = 0;
  }
}

static void aq_ub_feedback(int *sol_vertices, int sol_size, WeightSum ub_value){
  if(!AQ_ENABLED || !AQ_ACTIVE || !AQ_TOUCH_UB || sol_size <= 0 || INIT_UPPER_BOUND <= 0) return;
  float bonus = (float)((double)(INIT_UPPER_BOUND - ub_value) / INIT_UPPER_BOUND) * 0.5f;
  if(bonus <= 0) return;
  for(int i = 0; i < sol_size; i++){
    int v = sol_vertices[i];
    if(v >= 1 && v <= NB_NODE){
      AQ[v] += bonus; //给"出现在好的上界解中的顶点"额外增加信息素
      if(AQ[v] > AQ_TAU_MAX) AQ[v] = AQ_TAU_MAX;
    }
  }
}

static inline int compute_bounds(int k){
 
  memset(Loss,0,(NB_NODE+1)*sizeof(int));
  for(int node=1;node<=NB_NODE;node++){
      Subs[node]=1;
  }

  BEST_UPPER_BOUND=INIT_UPPER_BOUND;
  BEST_LOWER_BOUND=0;

  double BestAnt_Score = 0; //
  WeightSum BestAnt_LB = 0;

  do{

    if(get_utime()-read_time>time_limit)
      break;

    int cur_K;//蚂蚁数量
    if(AQ_ENABLED && AQ_ACTIVE){
      AQ_PHASE = 2;
      cur_K = AQ_NUM_ANTS;
    } else {
      AQ_PHASE = 1;
      cur_K = 1;
    }

    BestAnt_Score = 0;
    BestAnt_LB = 0;
    BestAnt_PairLength = 0;

    for(int ant = 0; ant < cur_K; ant++){ //
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

      if(ant_score > BestAnt_Score || BestAnt_PairLength == 0){
        BestAnt_Score = ant_score;
        BestAnt_LB = ant_lb;
        BestAnt_PairLength = ant_pair_length;
        memcpy(BestAnt_PairList, PairList, ant_pair_length * sizeof(LBPair));
      }

      for_each_undomed_node(node){
        if(domed(node)) clr_domed_status(node);
      }
    }
    //最优蚂蚁
    memcpy(PairList, BestAnt_PairList, BestAnt_PairLength * sizeof(LBPair));
    PairLength = BestAnt_PairLength;

    for_each_undomed_node(node){
      clr_domed_status(node);
      clr_selected_status(node);
      PairIndex[node] = NB_NODE;
    }
    for(int pi = 0; pi < PairLength; pi++){
      PairIndex[PairList[pi].target] = pi;
      set_selected_status(PairList[pi].target);
    }

    unimproved++;
    WeightSum bound = BestAnt_LB + CUR_BOUND;

    if(bound > BEST_LOWER_BOUND){
      unimproved = 0;
      BEST_LOWER_BOUND = bound;
    }

    if(compute_loss_and_upper_bound(bound)){
      break;
    }

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

  }while(unimproved<MaxIteration);
 
  return 1;
}

void check_final_solution(){
  printf("checking solution ====> ");
  for_each_vertex(node){
    clr_marked_status(node);
    clr_included_status(node);
  }
  for_each_vec_item(VEC_SOLUTION,int,it){
     int node=*it;
     assert(node>=1 && node<=NB_NODE);
     set_marked_status(node);
     assert(!included(node));
     set_included_status(node);
    for_each_neighbor(node,neibor){
        set_marked_status(neibor);
    }
  }
 
  for_each_vertex(node){
   
    if(deleted(node))continue;
   
    assert(marked(node));
    clr_marked_status(node);
  }

  for_each_vertex(node){
     if(deleted(node)){
      int flag=0;
      for_each_neighbor(node,neibor){
        if(included(neibor)){
	  flag=1;
	  break;
	}
      }
      assert(flag);
     }
   }
  printf(" passed !\n");
}


int ibmwds_init_bounds(int k,double *timeout){
  OPTIMAL=0;
  INIT_TIME=get_utime();
  if(k==0){
    build_problem_config();
    init_for_search();
  }else{
    aq_check_restart();
    double adaptive_alpha = ALPHA;
    if(USE_ADVANCED && AQ_Stagnation > 3)
      adaptive_alpha = ALPHA * 1.5;
    for(int i=0,node;i<USED(UNIT_STK);i++){
      node=ITEM(UNIT_STK,i);
      Beta[node]*=adaptive_alpha;
      #ifdef SMOOTH
      if(Beta[node]>=10.0)
	Beta[node]=1.0;
      #endif
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
  }
 
  compute_bounds(k);

  if(!FIRST_LOWER_BOUND){
    FIRST_LOWER_BOUND=BEST_LOWER_BOUND;
  }

  if(BEST_LOWER_BOUND>BEST_BEST_LOWER_BOUND)
    BEST_BEST_LOWER_BOUND=BEST_LOWER_BOUND;

  if(!FIRST_UPPER_BOUND)
    FIRST_UPPER_BOUND=BEST_UPPER_BOUND;

  if(FIRST_GAP == 0){
    FIRST_GAP=(FIRST_UPPER_BOUND-FIRST_LOWER_BOUND)/((double)FIRST_LOWER_BOUND);
    printf("First Gap  %lf\n",FIRST_GAP);
  }

  *timeout=get_utime()-INIT_TIME;
  printf("ALPHA %.4lf MaxIteration %d  TIMEOUT %lf\n",ALPHA,MaxIteration,*timeout);
  printf("%3d %10lld %10lld %10lld %11.4lf", k+1, BEST_LOWER_BOUND, BEST_BEST_LOWER_BOUND, BEST_UPPER_BOUND,*timeout);

  return OPTIMAL;
}


