"""Проверки формулы, слепого чтения, границ ёмкости и особых случаев."""
import unittest
import numpy as np
from kjb import embed, extract, positions


class KJBTests(unittest.TestCase):
    def setUp(self):
        self.image=np.full((64,64,3),128,dtype=np.uint8)
        self.bits=np.array([0,1,0,1,1,0,0,1],dtype=np.uint8)

    def test_formula_and_channels(self):
        result,_=embed(self.image,self.bits,"key",.1,1,3)
        y,x=positions(self.image.shape,len(self.bits),1,3,"key")
        self.assertEqual(result[y[0,0],x[0,0],2],115)
        self.assertEqual(result[y[1,0],x[1,0],2],141)
        np.testing.assert_array_equal(result[:,:,:2],self.image[:,:,:2])
        self.assertEqual(np.count_nonzero(result[:,:,2]!=128),10)

    def test_blind_roundtrip(self):
        result,_=embed(self.image,self.bits,"key",.1,31,3)
        got,_,_=extract(result,8,"key",31,3)
        np.testing.assert_array_equal(got,self.bits)

    def test_no_collisions(self):
        y,x=positions((64,64,3),8,31,3,"key")
        self.assertEqual(np.unique(y*64+x).size,310)

    def test_capacity_boundary(self):
        image=np.full((5,5,3),128,dtype=np.uint8)
        embed(image,np.zeros(7,dtype=np.uint8),repeats=1,radius=1)
        with self.assertRaises(ValueError):
            embed(image,np.zeros(8,dtype=np.uint8),repeats=1,radius=1)

    def test_black_cannot_carry_signal(self):
        image=np.zeros((64,64,3),dtype=np.uint8)
        marked,_=embed(image,self.bits)
        np.testing.assert_array_equal(marked,image)

    def test_clipping_and_validation(self):
        white=np.full((64,64,3),255,dtype=np.uint8)
        marked,count=embed(white,self.bits,strength=1)
        self.assertGreater(count,0)
        self.assertEqual(marked.dtype,np.uint8)
        for bad in ([],[0,2],[0,-1],[0,.5]):
            with self.assertRaises(ValueError): embed(self.image,bad)
        with self.assertRaises(ValueError): embed(self.image,self.bits,strength=float('nan'))


if __name__=="__main__": unittest.main()
