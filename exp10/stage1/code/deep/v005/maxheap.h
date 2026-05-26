#include "basic.h"

class MAXHEAP
{
public:
	MAXHEAP(int capacity);
	~MAXHEAP();
	void swap(int p1, int p2);
	bool isLeaf(int index);
	int getLeftChild(int p);
	int getRightChild(int p);
	int getParent(int p);
	void adjust(int p);
	void insert(int val);
	int removeRoot();
	int remove(int p);
	int getRoot();
	int getSize();
	void changeVal(int val);

private:
	int* arr_;
	int* pos_;
	int size_;
	int capacity_;
};

MAXHEAP::MAXHEAP(int capacity)
{
	capacity_ = capacity;
	size_ = 0;
	arr_ = new int[capacity];
	pos_ = new int[capacity];
	memset(pos_, -1, capacity * sizeof(int));
}

MAXHEAP::~MAXHEAP()
{
	delete[] pos_;
	delete[] arr_;
}

void MAXHEAP::swap(int p1, int p2)
{
	int t = arr_[p1];
	arr_[p1] = arr_[p2];
	pos_[arr_[p1]] = p1;
	arr_[p2] = t;
	pos_[arr_[p2]] = p2;
}

bool MAXHEAP::isLeaf(int p)
{
	if ((p >= size_ / 2) && (p < size_))
		return true;
	return false;
}

int MAXHEAP::getLeftChild(int p)
{
	return (2 * p + 1);
}

int MAXHEAP::getRightChild(int p)
{
	return (2 * p + 2);
}

int MAXHEAP::getParent(int p)
{
	return (p - 1) / 2;
}

void MAXHEAP::adjust(int p)
{
	int j, rc;
	while (!isLeaf(p))
	{
		j = getLeftChild(p);
		rc = getRightChild(p);
		if ((rc < size_) && compare(v_Score[arr_[rc]], v_Cost[arr_[rc]], v_Score[arr_[j]], v_Cost[arr_[j]]) > 0)
			j = rc;
		if (compare(v_Score[arr_[p]], v_Cost[arr_[p]], v_Score[arr_[j]], v_Cost[arr_[j]]) > 0)
			return;
		swap(p, j);
		p = j;
	}
}

void MAXHEAP::insert(int val)
{
	int p = size_++;
	arr_[p] = val;
	pos_[val] = p;
	while (p != 0 && compare(v_Score[arr_[p]], v_Cost[arr_[p]], v_Score[arr_[getParent(p)]], v_Cost[arr_[getParent(p)]]) > 0)
	{
		swap(p, getParent(p));
		p = getParent(p);
	}
}

int MAXHEAP::removeRoot()
{
	swap(0, --size_);
	if (size_ != 0)
		adjust(0);
	return arr_[size_];
}

int MAXHEAP::remove(int p)
{
	if (p == (size_ - 1))
		size_--;
	else
	{
		swap(p, --size_);
		while ((p != 0) && compare(v_Score[arr_[p]], v_Cost[arr_[p]], v_Score[arr_[getParent(p)]], v_Cost[arr_[getParent(p)]]) > 0)
		{
			swap(p, getParent(p));
			p = getParent(p);
		}
		if (size_ != 0)
			adjust(p);
	}
	return arr_[size_];
}

int MAXHEAP::getRoot()
{
	return arr_[0];
}

int MAXHEAP::getSize()
{
	return size_;
}

void MAXHEAP::changeVal(int val)
{
	int p = pos_[val];
	remove(p);
	insert(val);
}