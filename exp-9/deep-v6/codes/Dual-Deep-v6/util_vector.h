#include <stdlib.h>
#include <assert.h>

#ifndef V6R_UTIL_VECTOR_JH
#define V6R_UTIL_VECTOR_JH

#define VEC_DECLARE(T,tName)			\
  typedef struct {				\
    T *addr;					\
    unsigned used;				\
    unsigned capacity;				\
  }tName

	

#define push_back(Vec,T,Val)					\
  do{								\
    assert(Vec->used<=Vec->capacity);				\
    if(Vec->used==Vec->capacity){                               \
	printf("realloc vector " #Vec " ...\n");		\
      int size=Vec->capacity*2;					\
      Vec->addr=(T *)realloc(Vec->addr,(size+1)*sizeof(T));	\
      assert(Vec->addr!=NULL);					\
      Vec->capacity=size;					\
    }								\
    assert(Vec->used<Vec->capacity);				\
    *(Vec->addr+Vec->used)=(Val);				\
    (Vec->used)++;						\
  }while(0)



#define create_stack(Vec,VEC_TYPE,ITEM_TYPE,len)			\
  do{									\
    assert(len>0);							\
    unsigned size=(len);						\
    Vec=(VEC_TYPE *)calloc(1,sizeof(VEC_TYPE));				\
    assert(Vec!=NULL);							\
    (Vec)->addr=(ITEM_TYPE *)malloc((size+1)*sizeof(ITEM_TYPE));	\
    assert((Vec)->addr!=NULL);						\
    (Vec)->capacity=size;						\
    (Vec)->used=0;							\
  }while(0)



#define for_each_vec_item(Vec,T,It) for(T *It=Vec->addr, *__end=Vec->addr+Vec->used;It != __end;It++)

#define remove_value_from_vector(Vec,T,Val)                             \
do{									\
   for(T *It=Vec->addr, *__end=Vec->addr+Vec->used;It != __end;)        \
    if(*It==Val){                                                       \
        Vec->used--;*It=*(Vec->addr+Vec->used);                         \
        __end--;                                                        \
    }else                                                               \
      It++;                                                             \
}while(0)

#define ITEM(VEC,IDX) (VEC->addr[(IDX)])
#define USED(VEC) (VEC->used)
#define LastITEM(VEC) (*(VEC->addr+VEC->used-1))
#define TAIL(VEC) (VEC->addr+VEC->used-1)
#define HEAD(VEC) (VEC->addr)

VEC_DECLARE(int,VEC_INT);
VEC_DECLARE(unsigned,VEC_UINT);


#endif 
