#include "dominating2020_short.h"

int main(int argc, char* argv[])
{
  double gap_thd=0.01;
  if(argc<5){
    printf("Missing Parameters! USAGE: deepopt instance cutoff seed alpha \n");
    return 1;
  }
  long long int Best_Best_Cost=0;
  string file_name = argv[1];
  time_Cutoff = atoi(argv[2]);
  Seed = atoi(argv[3]);
  double pre_round_time=0;
  ALPHA=1+atoi(argv[4])/100.0;
  //gap_thd=atoi(argv[5])/100.0;
  
  printf("With  Parameters CUTOFF %d SEED %d  ALPHA = %.3lf \n", time_Cutoff ,Seed,  ALPHA);

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
	 timeout=time_Cutoff-used_time;
	 if(i==1)printf("\n Switch to original search , timeout %lf....\n",timeout);

	 constructInit();
       }
      #ifndef NMLS

      if(used_time>time_Cutoff){
	printf("\n");
	break;
      }
      if(used_time>time_Cutoff/1.5){
	timeout=time_Cutoff-used_time;
      }
      #endif
      localSearch(timeout);
      checkBestSol();
      if(Best_Best_Cost==0 || sol_Best_Cost<Best_Best_Cost)
	Best_Best_Cost=sol_Best_Cost;
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
