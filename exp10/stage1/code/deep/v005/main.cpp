#include "dominating2020_short.h"

int main(int argc, char* argv[])
{
  double gap_thd=0.01;
  if(argc<5){
    printf("USAGE: dual-deep-v6 instance cutoff seed alpha [K] [rho] [q0] [beta]\n");
    return 1;
  }
  long long int Best_Best_Cost=0;
  string file_name = argv[1];
  time_Cutoff = atoi(argv[2]);
  Seed = atoi(argv[3]);
  double pre_round_time=0;
  ALPHA=1+atoi(argv[4])/100.0;

  if(argc>5) AQ_NUM_ANTS = atoi(argv[5]);
  if(argc>6) AQ_RHO     = atof(argv[6]);
  if(argc>7) AQ_Q0      = atof(argv[7]);
  if(argc>8) AQ_BETA    = atof(argv[8]);
  const char *aq_mode = getenv("MWDS_AQ_MODE");
  int force_dbs = (aq_mode && string(aq_mode) == "dbs");
  const char *safe_min_gap_env = getenv("MWDS_AQ_MIN_FIRST_GAP");
  const char *deep_min_nodes_env = getenv("MWDS_DEEP_AQ_MIN_NODES");
  const char *deep_min_density_env = getenv("MWDS_DEEP_AQ_MIN_DENSITY");
  const char *deep_density_env = getenv("MWDS_DEEP_AQ_MAX_DENSITY");
  double aq_min_first_gap = safe_min_gap_env ? atof(safe_min_gap_env) : 0.05;
  int deep_aq_min_nodes = deep_min_nodes_env ? atoi(deep_min_nodes_env) : 800;
  double deep_aq_min_density = deep_min_density_env ? atof(deep_min_density_env) : 5.0;
  double deep_aq_max_density = deep_density_env ? atof(deep_density_env) : 10.0;
  
  printf("With  Parameters CUTOFF %d SEED %d  ALPHA = %.3lf  K=%d RHO=%.2f Q0=%.2f BETA=%.1f AQ_MODE=%s\n",
         time_Cutoff, Seed, ALPHA, AQ_NUM_ANTS, AQ_RHO, AQ_Q0, AQ_BETA,
         aq_mode ? aq_mode : "auto");

  int i=0;
  srand(Seed);
  double read_time, reduce_time,solve_time;
  printf("Reading  graph ... ");
  time_Start = chrono::steady_clock::now();
  if (readGraph(file_name) != 0) return 0;
  printf(" time %lf  \n",read_time=getTimeElapsed());

  time_Start = chrono::steady_clock::now();

  printf("Reducing graph ... ");
  reduceGraph();
  printf(" time %lf  \n",reduce_time=getTimeElapsed());

  double density = (double)NB_EDGE / NB_NODE;
  USE_ADVANCED = (NB_NODE >= 800 && density <= 15.0) ? 1 : 0;
  int structure_blocks_aq = (NB_NODE < deep_aq_min_nodes ||
                             density < deep_aq_min_density ||
                             density > deep_aq_max_density);
  printf("[v6] |V|=%d |E|=%d density=%.2f USE_ADVANCED=%d SAFE_AQ_MIN_GAP=%.3f DEEP_AQ_RANGE=[%d, %.2f, %.2f] structure_blocks_aq=%d\n",
         NB_NODE, NB_EDGE, density, USE_ADVANCED, aq_min_first_gap,
	 deep_aq_min_nodes, deep_aq_min_density, deep_aq_max_density,
	 structure_blocks_aq);

  double timeout=0;
 
  printf("#Rd        #LB        #LB*       #UB       #Time        #UB+        #UB*      #Time      #TotalTime\n");
  while(1){
    
    double _time=getTimeElapsed();
    if(_time>=time_Cutoff || _time/time_Cutoff>0.999)
      break;
   
    round_time_Start=chrono::steady_clock::now();
    reset_config();
      
    if(!ibmwds_init_bounds(i++,&timeout)){
       _round_time_Start = chrono::steady_clock::now();
       double used_time=getTimeElapsed();

       int first_gap_blocks_aq = (FIRST_GAP < aq_min_first_gap);

       if(force_dbs || structure_blocks_aq || first_gap_blocks_aq){
	 if(i==1)printf("\n Switch to DBS-only search, timeout %lf....\n",timeout);
	 if(i==1 && structure_blocks_aq)
	   printf(" [Online-safe AQ structure guard] |V|=%d density=%.2f outside [%d, %.2f, %.2f], disabling AQ\n",
		  NB_NODE, density, deep_aq_min_nodes, deep_aq_min_density, deep_aq_max_density);
	 if(i==1 && first_gap_blocks_aq)
	   printf(" [Online-safe AQ first-gap guard] FIRST_GAP %.4f < %.4f, disabling AQ\n",
		  FIRST_GAP, aq_min_first_gap);
	 AQ_ENABLED = 0;
	 AQ_ACTIVE = 0;
	 AQ_TOUCH_UB = 0;
	 constructInit();
       }else if(FIRST_GAP < gap_thd){
	 if(i==1)printf("\n Switch to dual bound search, timeout %lf....\n",timeout);
	 AQ_ENABLED = 0;
	 AQ_ACTIVE = 0;
	 AQ_TOUCH_UB = 0;
	 newConstructInit();
       }else {
	 if(i==1){
	   printf("\n Switch to original search + AQ boost, timeout %lf....\n",timeout);
	   AQ_ENABLED = 1;
	   AQ_ACTIVE = 1;
	   AQ_TOUCH_UB = 0;
	   double rl_deadline = time_Cutoff * 0.15;
	   int rl_stag = 0;
	   WeightSum rl_prev_lb = BEST_BEST_LOWER_BOUND;
	   while(getTimeElapsed() < rl_deadline){
	     round_time_Start=chrono::steady_clock::now();
	     reset_config();
	     if(ibmwds_init_bounds(i++,&timeout)){
	       break;
	     }
	     if(BEST_BEST_LOWER_BOUND > rl_prev_lb){
	       rl_stag = 0;
	       rl_prev_lb = BEST_BEST_LOWER_BOUND;
	     } else {
	       rl_stag++;
	     }
	     if(rl_stag >= 2){
	       printf(" [AQ guard] no early LB gain, disabling AQ stag=%d at %.1f%%\n",
		      rl_stag, getTimeElapsed()/time_Cutoff*100);
	       AQ_ENABLED = 0;
	       AQ_ACTIVE = 0;
	       AQ_TOUCH_UB = 0;
	       break;
	     }
	   }
	 }
	 timeout=time_Cutoff-getTimeElapsed();
	 constructInit();
       }
      #ifndef NMLS

      if(getTimeElapsed()>time_Cutoff){
	printf("\n");
	break;
      }
      if(getTimeElapsed()>time_Cutoff/1.5){
	timeout=time_Cutoff-getTimeElapsed();
      }
      #endif
      localSearch(timeout);
      checkBestSol();
      if(Best_Best_Cost==0 || sol_Best_Cost<Best_Best_Cost){
	Best_Best_Cost=sol_Best_Cost;
	if(USE_ADVANCED)
	  aq_ub_feedback(sol_Best, sol_Best_Size, Best_Best_Cost);
      }
      printf("%11lld %11lld  %10.4lf    %10.4lf\n", sol_Best_Cost,Best_Best_Cost,time_Sol, getTimeElapsed());
      if(Best_Best_Cost==BEST_BEST_LOWER_BOUND)
	break;
    }else{
      break;
    }
  }
 
  if(OPTIMAL || Best_Best_Cost==0)
    Best_Best_Cost=BEST_UPPER_BOUND;
  double lgap= (BEST_BEST_LOWER_BOUND-FIRST_LOWER_BOUND)/(double)FIRST_LOWER_BOUND;
  double ugap= (FIRST_UPPER_BOUND-Best_Best_Cost)/(double)FIRST_UPPER_BOUND;
  double gap=(Best_Best_Cost-BEST_BEST_LOWER_BOUND)/(double)Best_Best_Cost;
  solve_time=getTimeElapsed();
  if(gap!=0)
    printf(">>> %s |V| %d |E| %d  (#LB %0.4lf %lld ---> %lld  %0.4lf  %lld <--- %lld  %.4lf #UB) "
	   , getInstanceName(argv[1]),NB_NODE,NB_EDGE,lgap, FIRST_LOWER_BOUND, BEST_BEST_LOWER_BOUND,gap, Best_Best_Cost,FIRST_UPPER_BOUND,ugap);
  else
    printf("\n>>> %s |V| %d |E| %d  (#LB %0.4lf %lld ---> %lld  ====  %lld <--- %lld  %.4lf #UB) "
	   ,getInstanceName(argv[1]),NB_NODE,NB_EDGE,lgap, FIRST_LOWER_BOUND, BEST_BEST_LOWER_BOUND, Best_Best_Cost,FIRST_UPPER_BOUND,ugap);

  printf(" #read_time %.4lf  #reduce_time %.4lf  #solve_time %.4lf  #total_time %.4lf\n ",read_time, reduce_time, solve_time,solve_time+read_time+reduce_time);
   
  freeAll();
  return 0;
}
