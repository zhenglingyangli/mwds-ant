#include <stdlib.h>
#include <assert.h>

#ifndef V6R_UTIL_HEAP_H
#define V6R_UTIL_HEAP_H

typedef struct MaxNodeHeap MaxHeap;
typedef struct node HeapNode;

void check_heap(MaxHeap *heap);

static const int INF=0x3f3f3f3f;
struct node {
  int key;
  float value;
};

struct MaxNodeHeap{
  unsigned size;
  unsigned capacity;
  HeapNode *array;
  int *index; 
  int (*comparator)(const HeapNode * ,const HeapNode *);
};

static MaxHeap *Node_Heap;

#define size_of_heap(H)  (H->size)
#define empty_heap(H)  (H->size==0)
#define inHeap(H,x) ((H)->index[x]>=0)

static inline unsigned int left  (int i) { return i*2+1; }
static inline unsigned int right (int i) { return (i+1)*2; }
static inline unsigned int parent(int i) { return (i-1) >> 1; }

static inline void shiftUp(MaxHeap *heap,int i)
{
    HeapNode x = heap->array[i];
    int p  = parent(i);
    while (i != 0 && x.value > heap->array[p].value){
        heap->array[i]= heap->array[p];
	heap->index[(heap->array[p]).key] = i;
        i = p;
        p = parent(p);
    }
    heap->array[i] = x;
    heap->index[x.key] = i;
}

/*
static int inHeap(MaxHeap *heap,int x){
  for(int i=0;i<heap->size;i++){
    if(heap->array[i].key==x){
      assert(heap->index[x]==i);
      return 1;
    }
  }
  return 0;
}
*/
static inline void shiftDown(MaxHeap *heap,int i)
{
  //  assert(heap->comparator);

    HeapNode x = heap->array[i];
    while (left(i) < heap->size){
      int child = (right(i) < heap->size && heap->array[right(i)].value>heap->array[left(i)].value) ? right(i) : left(i);
      if (heap->array[child].value<=x.value) break;
        heap->array[i] = heap->array[child];
	heap->index[(heap->array[i]).key] = i;
        i = child;
    }
    heap->array[i] = x;
    heap->index[x.key] = i;
}

static void insertHeap(MaxHeap *heap, int key,float val){
  //printf("insert %d , heap size %d\n",key,heap->size);
    assert(heap->size<=heap->capacity);
    assert(key<=heap->capacity);
    if(heap->size==heap->capacity) {
        int NewSize=2*(heap->capacity);
	printf("realloc heap %d....\n",heap->capacity);
        heap->array=(HeapNode *)(realloc(heap->array,(NewSize+1)*sizeof (HeapNode)));
	heap->index=(int *)(realloc(heap->index,(NewSize+1)*sizeof (int)));

	printf("realloc heap %d....\n",NewSize);
        assert((heap->array)!=NULL);
	assert((heap->index)!=NULL);
        heap->capacity=NewSize;
    }
    HeapNode x;
    x.key=key;
    x.value=val;
    heap->array[heap->size]=x;
    heap->index[key]=heap->size;
    heap->size++;
    if(heap->size>1)shiftUp(heap,heap->size-1);
}

static inline int node_cmp_for_MaxHeap(const HeapNode *A,const HeapNode *B) {
    if(A->value==B->value)
      return A->key<B->key;
    return A->value > B->value;
}

static inline void initHeap(MaxHeap *heap,int capacity,int (*cmp)(const HeapNode *, const HeapNode*)){
  heap->array=(HeapNode *)calloc(capacity+1,sizeof(HeapNode));
  heap->index=(int *)calloc(capacity+1,sizeof(int));
  heap->capacity=capacity;
  heap->comparator=cmp;
  heap->size=0;
  assert(heap->array!=NULL && heap->index!=NULL);
  for(int i=0;i<=capacity;i++){
    heap->index[i]=-1;
  }
}

void print_heap(MaxHeap *heap);

static inline HeapNode removeTop(MaxHeap *heap)
{

  if(heap->size==0){
    HeapNode x;
    x.key=0;
    x.value=0;
    return x;
  }
  
  HeapNode x = heap->array[0];
  heap->index[x.key]=-1;

  heap->size--;
  if(heap->size){
    heap->array[0] = heap->array[heap->size];
    heap->index[heap->array[0].key]=0;
  }
 
  if (heap->size > 1) shiftDown(heap, 0);
 
  return x;
}

void updateHeap(MaxHeap *heap,int key,float val)
{
  if (inHeap(heap,key)){
    int idx=heap->index[key];
    heap->array[idx].value=val;
    shiftUp(heap, heap->index[key]);
    shiftDown(heap, heap->index[key]);
  }else{
    insertHeap(heap, key,val);
  }
}

static inline void clearHeap(MaxHeap *heap){
  heap->size=0;
  for(int i=0;i<=heap->capacity;i++){
    heap->index[i]=-1;
  }
}


void check_heap(MaxHeap *heap){
  for(int i=0;i<heap->size;i++){
    HeapNode node=heap->array[i];

   
    assert(node.key>=1 && node.key<=heap->capacity);
    assert(heap->index[node.key]==i);
    
    if(left(i)<heap->size)
      assert(heap->array[left(i)].value<=heap->array[i].value);
    if(right(i)<heap->size)
      assert(heap->array[right(i)].value<=heap->array[i].value);
   
  }
}

void print_heap(MaxHeap *heap){
  printf("Heap: #size %d #capacity %d\n",heap->size,heap->capacity);
 for(int i=0;i<heap->size;i++){
   printf("%d %lf\n",heap->array[i].key,heap->array[i].value);

 }

}

#endif //V6R_UTIL_HEAP_H
