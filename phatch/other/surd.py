#!/usr/bin/python
#
# surd.py -- Rational Number Objects -- V1.1
#
# !!! REQUIRES PYTHON VERSION 1.2 OR LATER !!!
#
# Rational number class.  This module supports the creation and manipulation
# of surds, or rational numbers.  The alllowed operations are +, -, *, /, pow,
# and unary -. Reverse methods for mixing with non-surds are supplied.
# Floats are converted to surds by multiplying by the power of ten necessary
# to make them whole numbers.  For example, 4.6 would be treated as 46/10.
# Exponentiated numbers are not handled yet.
#
# In addition, the following operator overload methods are provided:
#    cmp
#    hash
#    call
#    repr
#    str
#    float
#    int
#    long
#
# Surds appear to work just fine with other math functions such as cos and log.
#
# Nick Seidenman
# SAIC, McLean
# nick@osg.saic.com

# gcd (m, n)
#   Uses a modified Euclidean algorithm to
#   return greatest common devisor of m & n.
#   Handy for reducing fractions.
#
#   (Thanks to GvR for the niftier version that uses tuple arithmetic!)

def gcd (m, n):
    while n:
	m, n = n, m % n
    return m

import math

class surd:

    def __init__ (self, num=0L, denom=1L):

	# If the constructor arguments were floats, we need to
	# convert them into a whole number divided by an exponent
	# of 10.
	if type (num) == type (0.0):  # Were we handed a float?
	    np = long (math.pow (10, len (`num - long(num)`) - 2))
	    nd = long (num * np)
	    if type (denom) == type (0.0):  # Is the denominator a float too?
		dp = long(math.pow (10, len (`denom - int(denom)`) - 2))
		dd = long (denom * dp)
		num = nd * dp
		denom = dd * np
	    else:
		num = nd
		denom = denom * np
	elif type (denom) == type (0.0): # Is the denom a float?
	    dp = long (pow (10, len (`denom - int(denom)`) - 2))
	    dd = long (denom * dp)
	    num = num * dp
	    denom = dd
	else:
	    num = long (num)
	    denom = long (denom)

	# Zero divisor is not allowed - nip this in the bud.
	if denom == 0:
	    raise ZeroDivisionError

	# Always want the sign to go with the numerator.
	if denom < 0:   # Think about it ;)
	    num = -num
	    denom = -denom

	# Reduct the fraction.
	if num > 0:
	    d = gcd (abs(num), abs (denom))
	else:
	    d = 1
	self.num = num / d
	self.denom = denom / d

    def __add__ (self, arg):
	if not hasattr (arg, 'denom'):
	    spam = long (arg)
	    arg = surd (spam)
	denom = self.denom * arg.denom
	num = self.denom * arg.num + arg.denom * self.num
	d = gcd (abs(num), abs(denom))
	return surd (num / d, denom / d)

    __radd__ = __add__

    def __sub__ (self, arg):
	if not hasattr (arg, 'denom'):
	    spam = long (arg)
	    arg = surd (spam)
	denom = self.denom * arg.denom
	num = self.num * arg.denom - arg.num * self.denom
	d = gcd (abs(num), abs(denom))
	return surd (num / d, denom / d)

    __rsub__ = __sub__

    def __mul__ (self, arg):
	if not hasattr (arg, 'denom'):
	    spam = long (arg)
	    arg = surd (spam)
	s = surd (self.num * arg.num, self.denom * arg.denom)
	d = gcd (abs(s.num), abs(s.denom))
	s.num = s.num / d
	s.denom = s.denom / d
	return s

    __rmul__ = __mul__

    def __div__ (self, arg):
	if not hasattr (arg, 'denom'):
	    spam = long (arg)
	    arg = surd (spam)
	s = surd (self.num * arg.denom, self.denom * arg.num)
	d = gcd (abs(s.num), abs(s.denom))
	s.num = s.num / d
	s.denom = s.denom / d
	if s.denom == 0: raise ZeroDivisionError
	return s

    __rdiv__ = __div__

    def __neg__ (self):
	return surd (-self.num, self.denom)

    def __abs__ (self):
	return surd (abs (self.num), abs (self.denom))

    def __int__ (self):
	return int (self.num) / int (self.denom)

    def __long__ (self):
	return long (self.num) / long (self.denom)

    def __float__ (self):
	return float (self.num) / float (self.denom)

    def __repr__ (self):
	return `self.num` + '/' + `self.denom`

    def __str__ (self):
	if self.denom == 1:
	    return `self.num`
	else:
	    spam = `self.num` + '/' + `self.denom`
	    return spam

    def __cmp__ (self, other):
	if not hasattr (other, 'denom'):
	    spam = long (other)
	    other = surd (spam)

	# Make sure we are dealing with a common denominator.
	spam = self.num * other.denom
	eggs = other.num * self.denom

	if spam < eggs:
	    return -1
	elif spam > eggs:
	    return 1
	else:
	    return 0

    def __hash__ (self):
	return hash (`self`)

    def __call__ (self, *args):
	return 0



########################################################
#
# T E S T    D R I V E R
#
########################################################

SurdTestError = 'SurdTestError'

import time

def test_error ():
    raise SurdTestError

def test_driver ():

    print 'testing surd ...'

    # Instantiation tests.
    a = surd () # Create without arguments
    if a != 0: test_error ()
    b = surd(10) # Create with just numerator.
    if b != 10: test_error ()
    c = surd (145, 15) # Create with explicit num & denom
    if c != surd (145, 15): test_error ()

    ra = surd (3.2)
    if ra != surd (32, 10): test_error ()
    rb = surd (12.0, 2)
    if rb != surd (6, 1): test_error ()
    rc = surd (1045.2, 2.5)
    if rc != surd (10452, 25): test_error ()
    rd = surd (12000, .05)
    if rd != surd (240000): test_error ()

    # Test GCD reduction.
    if (a + surd (29, 3)) != c: test_error ()

    # Arithmetic tests.
    r = b + c
    if r != surd (59, 3): test_error ()
    r = b * c
    if r != surd (290, 3): test_error ()
    r = b - c
    if r != surd (1, 3): test_error ()
    r = b / c
    if r != surd (30, 29): test_error ()
    r = -c
    if r != surd (-29, 3): test_error ()

    if c + 4 != surd (41, 3): test_error ()
    if c * 3 != surd (87, 3): test_error ()
    if c - 24 != surd (-43, 3): test_error ()
    if c / 13 != surd (29, 39): test_error ()

    # Comparison tests.
    if a == b: test_error ()
    if b < c: test_error ()
    if c < a: test_error ()
    if b == c: test_error ()
    if c != surd (290, 30): test_error ()
    if -b >= a: test_error ()

    # Sanity (div by zero) tests.
    try:
	z = surd (4, 0)
    except ZeroDivisionError:
	pass
    else:
	test_error ()

    try:
	z1 = surd (4)
	z2 = surd () # 0/1
	z = z1 / z2
    except ZeroDivisionError:
	pass
    else:
	test_error ()

    # Hash tests

    if hash (a) != hash ('0L/1L'): test_error ()
    if hash (b) != hash ('10L/1L'): test_error ()
    if hash (c) != hash ('29L/3L'): test_error ()
    if hash (c) == hash (b): test_error ()
    if hash (c) == hash (a): test_error ()
    if hash (c) == hash (-c): test_error ()
    # Sign should always go on numerator ...
    if hash (surd (4, -3)) != hash ('-4L/3L'): test_error ()
    if hash (surd (-14, -3)) != hash ('14L/3L'): test_error ()

    # Call tests.
    if a(): test_error ()
    if b(): test_error ()
    if c(): test_error ()

    # Math function tests. (Not by any means exhausive, but I believe
    # representative.
    m = surd (pow (13.2, 2.5))
    if `float(m)` != `math.pow (13.2, 2.5)`: test_error ()
    m = surd (math.sin (30))
    if `float(m)` != `math.sin (30)`: test_error ()

    # If we made it here we passed every test.
    print 'all surd tests passed.'

    # B E N C H M A R K S

    # Addition.
    start_time = time.time ()
    a = surd ()
    for i in range (0, 1000):
	a = a + surd (4, 3)
    print '1000 additions in ', time.time () - start_time, 'seconds'

    # Subtraction.
    start_time = time.time ()
    a = surd (10)
    for i in range (0, 1000):
	a = a - surd (4, 3)
    print '1000 subtractions in ', time.time () - start_time, 'seconds'

    # Multiplication.
    start_time = time.time ()
    a = surd (3.2)
    b = surd (2.1)
    for i in range (0, 1000):
	c = a * b
    print '1000 multiplications in ', time.time () - start_time, 'seconds'

    # Division.
    start_time = time.time ()
    a = surd (4.2)
    b = surd (2.1)
    for i in range (0, 1000):
	c = a / b
    print '1000 divisions in ', time.time () - start_time, 'seconds'


if __name__ == '__main__':
    test_driver ()
