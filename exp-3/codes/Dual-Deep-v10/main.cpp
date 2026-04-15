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
  
  printf("With  Parameters CUTOFF %d SEED %d  ALPHA = %.3lf  K=%d RHO=%.2f Q0=%.2f BETA=%.1f\n",
         time_Cutoff, Seed, ALPHA, AQ_NUM_ANTS, AQ_RHO, AQ_Q0, AQ_BETA);

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
  printf("[v10] |V|=%d |E|=%d density=%.2f USE_ADVANCED=%d\n",
         NB_NODE, NB_EDGE, density, USE_ADVANCED);

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

       if(FIRST_GAP < gap_thd){
	 if(i==1)printf("\n Switch to dual bound search, timeout %lf....\n",timeout);
	 newConstructInit();
       }else {
	 if(i==1){
	   printf("\n Switch to original search + AQ boost, timeout %lf....\n",timeout);
	   AQ_ENABLED = 1;
	   double rl_deadline = time_Cutoff * 0.15;
	   int rl_stag = 0;
	   WeightSum rl_prev_lb = 0;
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
	     if(rl_stag >= 15){
	       printf(" [RL early exit] stag=%d at %.1f%%\n",
		      rl_stag, getTimeElapsed()/time_Cutoff*100);
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
