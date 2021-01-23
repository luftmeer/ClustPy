"""
Hartigan, J. A.; Hartigan, P. M. The Dip Test of Unimodality. The Annals
of Statistics 13 (1985), no. 1, 70--84. doi:10.1214/aos/1176346577.
http://projecteuclid.org/euclid.aos/1176346577.

Credit for Dip implementation:
Johannes Bauer, Python implementation of Hartigan's dip test, Jun 17, 2015,
commit a0e3d448a4b266f54ec63a5b3d5be351fbd1db1c,
https://github.com/tatome/dip_test

and

https://github.com/alimuldal/diptest

and

Dario Ringach <dario@wotan.cns.nyu.edu>, Martin Maechler <maechler@stat.math.ethz.ch>
"""

import numpy as np
import os
import platform
import ctypes

PVAL_BY_TABLE = 0
PVAL_BY_BOOT = 1
PVAL_BY_FUNCTION = 2

CAN_C_BE_USED = True
C_DIP_FILE = None

def dip(X, just_dip=False, is_data_sorted=False, use_c=True, debug=False):
    global CAN_C_BE_USED
    assert X.ndim == 1, "Data must be 1-dimensional for the dip-test. Your shape:{0}".format(X.shape)
    N = len(X)
    if not is_data_sorted:
        X = np.sort(X)
    if N < 4 or X[0] == X[-1]:
        d = 0.0
        return d if just_dip else (d, None, None)
    if use_c and load_c_dip_file():
        # Prepare data to match C data types
        X = np.asarray(X, dtype=np.float64)
        X_c = X.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
        N_c = np.array([N]).ctypes.data_as(ctypes.POINTER(ctypes.c_int))
        dip_value = np.zeros(1, dtype=np.float).ctypes.data_as(ctypes.POINTER(ctypes.c_double))
        low_high = np.zeros(4).ctypes.data_as(ctypes.POINTER(ctypes.c_int))
        modal_triangle = np.zeros(3).ctypes.data_as(ctypes.POINTER(ctypes.c_int))
        gcm = np.zeros(N).ctypes.data_as(ctypes.POINTER(ctypes.c_int))
        lcm = np.zeros(N).ctypes.data_as(ctypes.POINTER(ctypes.c_int))
        mn = np.zeros(N).ctypes.data_as(ctypes.POINTER(ctypes.c_int))
        mj = np.zeros(N).ctypes.data_as(ctypes.POINTER(ctypes.c_int))
        debug_c = np.array([1 if debug else 0]).ctypes.data_as(ctypes.POINTER(ctypes.c_int))
        # Execute C dip test
        _ = C_DIP_FILE.diptst(X_c, N_c, dip_value, low_high, modal_triangle, gcm, lcm, mn, mj, debug_c)
        dip_value = dip_value[0]
        if just_dip:
            return dip_value
        else:
            low_high = (low_high[0], low_high[1], low_high[2], low_high[3])
            modal_triangle = (modal_triangle[0], modal_triangle[1], modal_triangle[2])
            return dip_value, low_high, modal_triangle
    else:
        return dip_python_port(X, just_dip, debug)


def load_c_dip_file():
    global C_DIP_FILE
    global CAN_C_BE_USED
    if CAN_C_BE_USED and C_DIP_FILE is None:
        files_path = os.path.dirname(__file__)
        if platform.system() == "Windows":
            dip_compiled = files_path + "/dip.dll"
        else:
            dip_compiled = files_path + "/dip.so"
        if os.path.isfile(dip_compiled):
            # load c file
            try:
                C_DIP_FILE = ctypes.CDLL(dip_compiled)
                C_DIP_FILE.diptst.restype = None
                C_DIP_FILE.diptst.argtypes = [ctypes.POINTER(ctypes.c_double),
                                         ctypes.POINTER(ctypes.c_int),
                                         ctypes.POINTER(ctypes.c_double),
                                         ctypes.POINTER(ctypes.c_int),
                                         ctypes.POINTER(ctypes.c_int),
                                         ctypes.POINTER(ctypes.c_int),
                                         ctypes.POINTER(ctypes.c_int),
                                         ctypes.POINTER(ctypes.c_int),
                                         ctypes.POINTER(ctypes.c_int),
                                         ctypes.POINTER(ctypes.c_int)]
                return True
            except Exception as e:
                print("[WARNING] C implementation can not be used for dip calculation.")
                print(e)
                CAN_C_BE_USED = False
                return False
        else:
            print("[WARNING] C implementation can not be used for dip calculation.")
            CAN_C_BE_USED = False
            return False
    elif CAN_C_BE_USED:
        return True
    else:
        return False


def dip_python_port(X, just_dip=False, is_data_sorted=False, debug=False):
    assert X.ndim == 1, "Data must be 1-dimensional for the dip-test. Your shape:{0}".format(X.shape)
    N = len(X)
    if not is_data_sorted:
        X = np.sort(X)
    if N < 4 or X[0] == X[-1]:
        d = 0.0
        return d if just_dip else (d, None, None)

    low = 0
    high = N - 1
    dip_value = 0.0

    modaltriangle_i1 = None
    modaltriangle_i2 = None
    modaltriangle_i3 = None
    best_low = None
    best_high = None

    # Establish the indices mn[1..n] over which combination is necessary for the convex MINORANT (GCM) fit.
    mn = np.zeros(N, dtype=int)
    mn[0] = 0
    for j in range(1, N):
        mn[j] = j - 1
        while True:
            mnj = mn[j]
            mnmnj = mn[mnj]
            if mnj == 0 or (X[j] - X[mnj]) * (mnj - mnmnj) < (X[mnj] - X[mnmnj]) * (j - mnj):
                break
            mn[j] = mnmnj
    # Establish the indices   mj[1..n]  over which combination is necessary for the concave MAJORANT (LCM) fit.
    mj = np.zeros(N, dtype=int)
    mj[N - 1] = N - 1
    for k in range(N - 2, -1, -1):
        mj[k] = k + 1
        while True:
            mjk = mj[k]
            mjmjk = mj[mjk]
            if mjk == N - 1 or (X[k] - X[mjk]) * (mjk - mjmjk) < (X[mjk] - X[mjmjk]) * (k - mjk):
                break
            mj[k] = mjmjk

    gcm = np.zeros(N, dtype=int)  # np.arange(N)
    lcm = np.zeros(N, dtype=int)  # np.arange(N, -1, -1)
    while True:
        gcm[0] = high
        i = 0
        while gcm[i] > low:
            gcm[i + 1] = mn[gcm[i]]
            i += 1
        ig = i
        l_gcm = i
        ix = ig - 1

        lcm[0] = low
        i = 0
        while lcm[i] < high:
            lcm[i + 1] = mj[lcm[i]]
            i += 1
        ih = i
        l_lcm = i
        iv = 1

        if debug:
            print("'dip': LOOP-BEGIN: 2n*D= {0}  [low,high] = [{1},{2}]:".format(dip_value, low, high))
            print("gcm[0:{0}] = {1}".format(l_gcm, gcm[:l_gcm + 1]))
            print("lcm[0:{0}] = {1}".format(l_lcm, lcm[:l_lcm + 1]))
        d = 0.0
        if l_gcm != 1 or l_lcm != 1:
            if debug:
                print("  while(gcm[ix] != lcm[iv])")
            while True:
                gcmix = gcm[ix]
                lcmiv = lcm[iv]
                if gcmix > lcmiv:
                    gcmil = gcm[ix + 1]
                    dx = (lcmiv - gcmil + 1) - (X[lcmiv] - X[gcmil]) * (gcmix - gcmil) / (X[gcmix] - X[gcmil])
                    iv += 1
                    if dx >= d:
                        d = dx
                        ig = ix + 1
                        ih = iv - 1
                        if debug:
                            print("L({0},{1})".format(ig, ih))
                else:
                    lcmivl = lcm[iv - 1]
                    dx = (X[gcmix] - X[lcmivl]) * (lcmiv - lcmivl) / (X[lcmiv] - X[lcmivl]) - (gcmix - lcmivl - 1)
                    ix -= 1
                    if dx >= d:
                        d = dx
                        ig = ix + 1
                        ih = iv
                        if debug:
                            print("G({0},{1})".format(ig, ih))
                if ix < 0:
                    ix = 0
                if iv > l_lcm:
                    iv = l_lcm
                if debug:
                    print("  --> ix = {0}, iv = {1}".format(ix, iv))
                if gcm[ix] == lcm[iv]:
                    break
        else:
            d = 0.0
            if debug:
                print("  ** (l_lcm,l_gcm) = ({0},{1}) ==> d := {2}".format(l_lcm, l_gcm, d))
        if d < dip_value:
            break
        if debug:
            print("  calculating dip ..")

        j_l = None
        j_u = None
        lcm_modalTriangle_i1 = None
        lcm_modalTriangle_i3 = None
        gcm_modalTriangle_i1 = None
        gcm_modalTriangle_i3 = None

        dip_l = 0
        for j in range(ig, l_gcm):
            max_t = 1
            j_ = None
            jb = gcm[j + 1]
            je = gcm[j]
            if je - jb > 1 and X[je] != X[jb]:
                C = (je - jb) / (X[je] - X[jb])
                for jj in range(jb, je + 1):
                    t = (jj - jb + 1) - (X[jj] - X[jb]) * C
                    if max_t < t:
                        max_t = t
                        j_ = jj
            if dip_l < max_t:
                dip_l = max_t
                j_l = j_
                gcm_modalTriangle_i1 = jb
                gcm_modalTriangle_i3 = je

        dip_u = 0
        for j in range(ih, l_lcm):
            max_t = 1
            j_ = None
            jb = lcm[j]
            je = lcm[j + 1]
            if je - jb > 1 and X[je] != X[jb]:
                C = (je - jb) / (X[je] - X[jb])
                for jj in range(jb, je + 1):
                    t = (X[jj] - X[jb]) * C - (jj - jb - 1)
                    if max_t < t:
                        max_t = t
                        j_ = jj
            if dip_u < max_t:
                dip_u = max_t
                j_u = j_
                lcm_modalTriangle_i1 = jb
                lcm_modalTriangle_i3 = je

        if debug:
            print(" (dip_l, dip_u) = ({0}, {1})".format(dip_l, dip_u))

        if dip_u > dip_l:
            dip_new = dip_u
            j_best = j_u
            if debug:
                print(" -> new larger dip {0} (j_best = {1}) gcm-centred triple ({2},{3},{4})".format(dip_new, j_best,
                                                                                                      lcm_modalTriangle_i1,
                                                                                                      j_best,
                                                                                                      lcm_modalTriangle_i3))
        else:
            dip_new = dip_l
            j_best = j_l
            if debug:
                print(" -> new larger dip {0} (j_best = {1}) lcm-centred triple ({2},{3},{4})".format(dip_new, j_best,
                                                                                                      gcm_modalTriangle_i1,
                                                                                                      j_best,
                                                                                                      gcm_modalTriangle_i3))
        if dip_value < dip_new:
            dip_value = dip_new
            best_low = gcm[ig]
            best_high = lcm[ih]
            if dip_u > dip_l:
                modaltriangle_i1 = lcm_modalTriangle_i1
                modaltriangle_i2 = j_best
                modaltriangle_i3 = lcm_modalTriangle_i3
            else:
                modaltriangle_i1 = gcm_modalTriangle_i1
                modaltriangle_i2 = j_best
                modaltriangle_i3 = gcm_modalTriangle_i3

        if low == gcm[ig] and high == lcm[ih]:
            if debug:
                print("No improvement in  low = {0}  nor  high = {1} --> END".format(low, high))
            break
        low = gcm[ig]
        high = lcm[ih]
    dip_value /= (2 * N)
    # TODO: Better with best low best high?
    return dip_value if just_dip else (
        dip_value, (low, high, best_low, best_high), (modaltriangle_i1, modaltriangle_i2, modaltriangle_i3))


def dip_test(X, is_data_sorted=False, pval_strategy=PVAL_BY_TABLE, n_boots=2000, use_c=True, debug=False):
    """
    Hartigan & Hartigan's dip test for unimodality.
    For X ~ F i.i.d., the null hypothesis is that F is a unimodal distribution.
    The alternative hypothesis is that F is multimodal (i.e. at least bimodal).
    Other than unimodality, the dip test does not assume any particular null
    distribution.
    Arguments:
    -----------
    X:          [n,] array  containing the input data
    data_is_sorted:   boolean
    pval_calculation:  0: p-value is computed via linear interpolation of the tabulated critical values.
                1: p-value is computed using bootstrap samples from a
                uniform distribution.
                2: p-value is computed using an approximated sigmoid function
    n_boots:    if pval_calculation="boot", this sets the number of bootstrap samples to
                use for computing the p-value.
    Returns:
    -----------
    dip:    double, the dip statistic
    pval:   double, the p-value for the test
    Reference:
    -----------
        Hartigan, J. A., & Hartigan, P. M. (1985). The Dip Test of Unimodality.
        The Annals of Statistics.
    """
    n_points = X.shape[0]
    data_dip = dip(X, just_dip=True, is_data_sorted=is_data_sorted, use_c=use_c, debug=debug)
    pval = dip_pval(data_dip, n_points, pval_strategy, n_boots)
    return data_dip, pval


def dip_pval(data_dip, n_points, pval_strategy=PVAL_BY_TABLE, n_boots=2000):
    if n_points <= 4:
        pval = 1.0
    elif pval_strategy == PVAL_BY_BOOT:
        boot_dips = dip_boot_samples(n_points, n_boots)
        pval = np.mean(data_dip <= boot_dips)
    elif pval_strategy == PVAL_BY_TABLE:
        pval = _dip_pval_table(data_dip, n_points)
    elif pval_strategy == PVAL_BY_FUNCTION:
        pval = _dip_pval_function(data_dip, n_points)
    else:
        raise ValueError(
            "pval_strategy must be 0 (table), 1 (boot) or 2 (function). Your input: {0}".format(pval_strategy))
    return pval


def dip_boot_samples(n_points, n_boots):
    # random uniform vectors
    boot_samples = np.random.rand(n_boots, n_points)
    # faster to pre-sort
    boot_dips = np.array([dip(boot_s, just_dip=True, is_data_sorted=False) for boot_s in boot_samples])
    return boot_dips


"""
Dip p-value methods
"""


def _dip_pval_table(data_dip, n_points):
    N, SIG, CV = _dip_table_values()
    i1 = N.searchsorted(n_points, side='left')
    i0 = i1 - 1
    # if n falls outside the range of tabulated sample sizes, use the
    # critical values for the nearest tabulated n (i.e. treat them as
    # 'asymptotic')
    i0 = max(0, i0)
    i1 = min(N.shape[0] - 1, i1)
    # interpolate on sqrt(n)
    n0, n1 = N[[i0, i1]]
    fn = float(n_points - n0) / (n1 - n0)
    y0 = np.sqrt(n0) * CV[i0]
    y1 = np.sqrt(n1) * CV[i1]
    sD = np.sqrt(n_points) * data_dip
    pval = 1. - np.interp(sD, y0 + fn * (y1 - y0), SIG)
    return pval


def _dip_pval_function(data_dip, n_points):
    a = 1.0
    d = 0.0
    # Polynom fitting
    n = np.log(n_points)
    b = 7.63466648e+00 + (3.75363863e-01 * n) + (-5.91013944e-02 * n ** 2) + (4.70521924e-03 * n ** 3) + (
            -1.46365776e-04 * n ** 4)
    c = 2.44547986e-01 + (-8.91268608e-02 * n) + (1.30656578e-02 * n ** 2) + (-8.94635688e-04 * n ** 3) + (
            2.37116900e-05 * n ** 4)
    g = 1.44028297e+00 + (-3.14378648e-01 * n) + (6.10595736e-02 * n ** 2) + (-5.22384667e-03 * n ** 3) + (
            1.63970372e-04 * n ** 4)
    pval = d + (a - d) / (1 + (data_dip / c) ** b) ** g
    return pval


def _dip_table_values():
    N = np.array([4, 5, 6, 7, 8, 9, 10, 15, 20,
                  30, 50, 100, 200, 500, 1000, 2000, 5000, 10000,
                  20000, 40000, 72000])
    SIG = np.array([0., 0.01, 0.02, 0.05, 0.1, 0.2,
                    0.3, 0.4, 0.5, 0.6, 0.7, 0.8,
                    0.9, 0.95, 0.98, 0.99, 0.995, 0.998,
                    0.999, 0.9995, 0.9998, 0.9999, 0.99995, 0.99998,
                    0.99999, 1.])
    # [len(N), len(SIG)] table of critical values
    CV = np.array([[0.125, 0.125, 0.125, 0.125, 0.125, 0.125, 0.125, 0.125, 0.125, 0.125, 0.132559548782689,
                    0.157497369040235, 0.187401878807559, 0.20726978858736, 0.223755804629222, 0.231796258864192,
                    0.237263743826779, 0.241992892688593, 0.244369839049632, 0.245966625504691, 0.247439597233262,
                    0.248230659656638, 0.248754269146416, 0.249302039974259, 0.249459652323225, 0.24974836247845],
                   [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.108720593576329, 0.121563798026414, 0.134318918697053,
                    0.147298798976252, 0.161085025702604, 0.176811998476076, 0.186391796027944, 0.19361253363045,
                    0.196509139798845, 0.198159967287576, 0.199244279362433, 0.199617527406166, 0.199800941499028,
                    0.199917081834271, 0.199959029093075, 0.199978395376082, 0.199993151405815, 0.199995525025673,
                    0.199999835639211],
                   [0.0833333333333333, 0.0833333333333333, 0.0833333333333333, 0.0833333333333333,
                    0.0833333333333333, 0.0924514470941933, 0.103913431059949, 0.113885220640212, 0.123071187137781,
                    0.13186973390253, 0.140564796497941, 0.14941924112913, 0.159137064572627, 0.164769608513302,
                    0.179176547392782, 0.191862827995563, 0.202101971042968, 0.213015781111186, 0.219518627282415,
                    0.224339047394446, 0.229449332154241, 0.232714530449602, 0.236548128358969, 0.2390887911995,
                    0.240103566436295, 0.244672883617768],
                   [0.0714285714285714, 0.0714285714285714, 0.0714285714285714, 0.0725717816250742,
                    0.0817315478539489, 0.09405901819225269, 0.103244490800871, 0.110964599995697,
                    0.117807846504335, 0.124216086833531, 0.130409013968317, 0.136639642123068, 0.144240669035124,
                    0.159903395678336, 0.175196553271223, 0.184118659121501, 0.191014396174306, 0.198216795232182,
                    0.202341010748261, 0.205377566346832, 0.208306562526874, 0.209866047852379, 0.210967576933451,
                    0.212233348558702, 0.212661038312506, 0.21353618608817],
                   [0.0625, 0.0625, 0.06569119945032829, 0.07386511360717619, 0.0820045917762512,
                    0.0922700601131892, 0.09967371895993631, 0.105733531802737, 0.111035129847705,
                    0.115920055749988, 0.120561479262465, 0.125558759034845, 0.141841067033899, 0.153978303998561,
                    0.16597856724751, 0.172988528276759, 0.179010413496374, 0.186504388711178, 0.19448404115794,
                    0.200864297005026, 0.208849997050229, 0.212556040406219, 0.217149174137299, 0.221700076404503,
                    0.225000835357532, 0.233772919687683],
                   [0.0555555555555556, 0.0613018090298924, 0.0658615858179315, 0.0732651142535317,
                    0.0803941629593475, 0.0890432420913848, 0.0950811420297928, 0.09993808978110461,
                    0.104153560075868, 0.108007802361932, 0.112512617124951, 0.122915033480817, 0.136412639387084,
                    0.146603784954019, 0.157084065653166, 0.164164643657217, 0.172821674582338, 0.182555283567818,
                    0.188658833121906, 0.194089120768246, 0.19915700809389, 0.202881598436558, 0.205979795735129,
                    0.21054115498898, 0.21180033095039, 0.215379914317625],
                   [0.05, 0.0610132555623269, 0.0651627333214016, 0.0718321619656165, 0.077966212182459,
                    0.08528353598345639, 0.09032041737070989, 0.0943334983745117, 0.0977817630384725,
                    0.102180866696628, 0.109960948142951, 0.118844767211587, 0.130462149644819, 0.139611395137099,
                    0.150961728882481, 0.159684158858235, 0.16719524735674, 0.175419540856082, 0.180611195797351,
                    0.185286416050396, 0.191203083905044, 0.195805159339184, 0.20029398089673, 0.205651089646219,
                    0.209682048785853, 0.221530282182963],
                   [0.0341378172277919, 0.0546284208048975, 0.0572191260231815, 0.0610087367689692,
                    0.06426571373304441, 0.06922341079895911, 0.0745462114365167, 0.07920308789817621,
                    0.083621033469191, 0.08811984822029049, 0.093124666680253, 0.0996694393390689,
                    0.110087496900906, 0.118760769203664, 0.128890475210055, 0.13598356863636, 0.142452483681277,
                    0.150172816530742, 0.155456133696328, 0.160896499106958, 0.166979407946248, 0.17111793515551,
                    0.175900505704432, 0.181856676013166, 0.185743454151004, 0.192240563330562],
                   [0.033718563622065, 0.0474333740698401, 0.0490891387627092, 0.052719998201553,
                    0.0567795509056742, 0.0620134674468181, 0.06601638720690479, 0.06965060750664009,
                    0.07334377405927139, 0.07764606628802539, 0.0824558407118372, 0.08834462700173699,
                    0.09723460181229029, 0.105130218270636, 0.114309704281253, 0.120624043335821, 0.126552378036739,
                    0.13360135382395, 0.138569903791767, 0.14336916123968, 0.148940116394883, 0.152832538183622,
                    0.156010163618971, 0.161319225839345, 0.165568255916749, 0.175834459522789],
                   [0.0262674485075642, 0.0395871890405749, 0.0414574606741673, 0.0444462614069956,
                    0.0473998525042686, 0.0516677370374349, 0.0551037519001622, 0.058265005347493,
                    0.0614510857304343, 0.0649164408053978, 0.0689178762425442, 0.0739249074078291,
                    0.08147913793901269, 0.0881689143126666, 0.0960564383013644, 0.101478558893837,
                    0.10650487144103, 0.112724636524262, 0.117164140184417, 0.121425859908987, 0.126733051889401,
                    0.131198578897542, 0.133691739483444, 0.137831637950694, 0.141557509624351, 0.163833046059817],
                   [0.0218544781364545, 0.0314400501999916, 0.0329008160470834, 0.0353023819040016,
                    0.0377279973102482, 0.0410699984399582, 0.0437704598622665, 0.0462925642671299,
                    0.048851155289608, 0.0516145897865757, 0.0548121932066019, 0.0588230482851366,
                    0.06491363240467669, 0.0702737877191269, 0.07670958860791791, 0.0811998415355918,
                    0.0852854646662134, 0.09048478274902939, 0.0940930106666244, 0.0974904344916743,
                    0.102284204283997, 0.104680624334611, 0.107496694235039, 0.11140887547015, 0.113536607717411,
                    0.117886716865312],
                   [0.0164852597438403, 0.022831985803043, 0.0238917486442849, 0.0256559537977579,
                    0.0273987414570948, 0.0298109370830153, 0.0317771496530253, 0.0336073821590387,
                    0.0354621760592113, 0.0374805844550272, 0.0398046179116599, 0.0427283846799166,
                    0.047152783315718, 0.0511279442868827, 0.0558022052195208, 0.059024132304226,
                    0.0620425065165146, 0.06580160114660991, 0.0684479731118028, 0.0709169443994193,
                    0.0741183486081263, 0.0762579402903838, 0.0785735967934979, 0.08134583568891331,
                    0.0832963013755522, 0.09267804230967371],
                   [0.0111236388849688, 0.0165017735429825, 0.0172594157992489, 0.0185259426032926,
                    0.0197917612637521, 0.0215233745778454, 0.0229259769870428, 0.024243848341112,
                    0.025584358256487, 0.0270252129816288, 0.0286920262150517, 0.0308006766341406,
                    0.0339967814293504, 0.0368418413878307, 0.0402729850316397, 0.0426864799777448,
                    0.044958959158761, 0.0477643873749449, 0.0497198001867437, 0.0516114611801451,
                    0.0540543978864652, 0.0558704526182638, 0.0573877056330228, 0.0593365901653878,
                    0.0607646310473911, 0.0705309107882395],
                   [0.00755488597576196, 0.0106403461127515, 0.0111255573208294, 0.0119353655328931,
                    0.0127411306411808, 0.0138524542751814, 0.0147536004288476, 0.0155963185751048,
                    0.0164519238025286, 0.017383057902553, 0.0184503949887735, 0.0198162679782071,
                    0.0218781313182203, 0.0237294742633411, 0.025919578977657, 0.0274518022761997,
                    0.0288986369564301, 0.0306813505050163, 0.0320170996823189, 0.0332452747332959,
                    0.0348335698576168, 0.0359832389317461, 0.0369051995840645, 0.0387221159256424,
                    0.03993025905765, 0.0431448163617178],
                   [0.00541658127872122, 0.00760286745300187, 0.007949878346447991, 0.008521651834359399,
                    0.00909775605533253, 0.009889245210140779, 0.0105309297090482, 0.0111322726797384,
                    0.0117439009052552, 0.012405033293814, 0.0131684179320803, 0.0141377942603047,
                    0.0156148055023058, 0.0169343970067564, 0.018513067368104, 0.0196080260483234,
                    0.0206489568587364, 0.0219285176765082, 0.0228689168972669, 0.023738710122235,
                    0.0248334158891432, 0.0256126573433596, 0.0265491336936829, 0.027578430100536, 0.0284430733108,
                    0.0313640941982108],
                   [0.00390439997450557, 0.00541664181796583, 0.00566171386252323, 0.00607120971135229,
                    0.0064762535755248, 0.00703573098590029, 0.00749421254589299, 0.007920878896017331,
                    0.008355737247680061, 0.00882439333812351, 0.00936785820717061, 0.01005604603884,
                    0.0111019116837591, 0.0120380990328341, 0.0131721010552576, 0.0139655122281969,
                    0.0146889122204488, 0.0156076779647454, 0.0162685615996248, 0.0168874937789415,
                    0.0176505093388153, 0.0181944265400504, 0.0186226037818523, 0.0193001796565433,
                    0.0196241518040617, 0.0213081254074584],
                   [0.00245657785440433, 0.00344809282233326, 0.00360473943713036, 0.00386326548010849,
                    0.00412089506752692, 0.00447640050137479, 0.00476555693102276, 0.00503704029750072,
                    0.00531239247408213, 0.00560929919359959, 0.00595352728377949, 0.00639092280563517,
                    0.00705566126234625, 0.0076506368153935, 0.00836821687047215, 0.008863578928549141,
                    0.00934162787186159, 0.009932186363240289, 0.0103498795291629, 0.0107780907076862,
                    0.0113184316868283, 0.0117329446468571, 0.0119995948968375, 0.0124410052027886,
                    0.0129467396733128, 0.014396063834027],
                   [0.00174954269199566, 0.00244595133885302, 0.00255710802275612, 0.00273990955227265,
                    0.0029225480567908, 0.00317374638422465, 0.00338072258533527, 0.00357243876535982,
                    0.00376734715752209, 0.00397885007249132, 0.00422430013176233, 0.00453437508148542,
                    0.00500178808402368, 0.00542372242836395, 0.00592656681022859, 0.00628034732880374,
                    0.00661030641550873, 0.00702254699967648, 0.00731822628156458, 0.0076065423418208,
                    0.00795640367207482, 0.008227052458435399, 0.00852240989786251, 0.00892863905540303,
                    0.009138539330002131, 0.009522345795667729],
                   [0.00119458814106091, 0.00173435346896287, 0.00181194434584681, 0.00194259470485893,
                    0.00207173719623868, 0.00224993202086955, 0.00239520831473419, 0.00253036792824665,
                    0.00266863168718114, 0.0028181999035216, 0.00299137548142077, 0.00321024899920135,
                    0.00354362220314155, 0.00384330190244679, 0.00420258799378253, 0.00445774902155711,
                    0.00469461513212743, 0.00499416069129168, 0.00520917757743218, 0.00540396235924372,
                    0.00564540201704594, 0.00580460792299214, 0.00599774739593151, 0.00633099254378114,
                    0.00656987109386762, 0.00685829448046227],
                   [0.000852415648011777, 0.00122883479310665, 0.00128469304457018, 0.00137617650525553,
                    0.00146751502006323, 0.00159376453672466, 0.00169668445506151, 0.00179253418337906,
                    0.00189061261635977, 0.00199645471886179, 0.00211929748381704, 0.00227457698703581,
                    0.00250999080890397, 0.00272375073486223, 0.00298072958568387, 0.00315942194040388,
                    0.0033273652798148, 0.00353988965698579, 0.00369400045486625, 0.00383345715372182,
                    0.00400793469634696, 0.00414892737222885, 0.0042839159079761, 0.00441870104432879,
                    0.00450818604569179, 0.00513477467565583],
                   [0.000644400053256997, 0.000916872204484283, 0.000957932946765532, 0.00102641863872347,
                    0.00109495154218002, 0.00118904090369415, 0.00126575197699874, 0.00133750966361506,
                    0.00141049709228472, 0.00148936709298802, 0.00158027541945626, 0.00169651643860074,
                    0.00187306184725826, 0.00203178401610555, 0.00222356097506054, 0.00235782814777627,
                    0.00248343580127067, 0.00264210826339498, 0.0027524322157581, 0.0028608570740143,
                    0.00298695044508003, 0.00309340092038059, 0.00319932767198801, 0.00332688234611187,
                    0.00339316094477355, 0.00376331697005859]])
    return N, SIG, CV


"""
Methods to calculate fast dip value
"""


def _gcm_(cdf, idxs):
    work_cdf = cdf
    work_idxs = idxs
    gcm = [work_cdf[0]]
    touchpoints = [0]
    while len(work_cdf) > 1:
        distances = work_idxs[1:] - work_idxs[0]
        slopes = (work_cdf[1:] - work_cdf[0]) / distances
        minslope = slopes.min()
        minslope_idx = np.where(slopes == minslope)[0][0] + 1
        gcm.extend(work_cdf[0] + distances[:minslope_idx] * minslope)
        touchpoints.append(touchpoints[-1] + minslope_idx)
        work_cdf = work_cdf[minslope_idx:]
        work_idxs = work_idxs[minslope_idx:]
    return np.array(np.array(gcm)), np.array(touchpoints)


def _lcm_(cdf, idxs):
    g, t = _gcm_(1 - cdf[::-1], idxs.max() - idxs[::-1])
    return 1 - g[::-1], len(cdf) - 1 - t[::-1]


def _touch_diffs_(part1, part2, touchpoints):
    diff = np.abs((part2[touchpoints] - part1[touchpoints]))
    return diff.max(), diff

def dip_fast(X, just_dip=False, is_data_sorted=False):
    """
        Compute the Hartigans' dip statistic either for a histogram of
        samples (with equidistant bins) or for a set of samples.
    """
    # Set precision to less than float64 since the subtraction in _lcm_ is having problems with the precision and
    # produces duplicates
    assert X.ndim == 1, "Data must be 1-dimensional for the dip-test"
    X = np.around(X, 15)
    idxs, histogram = np.unique(X, return_counts=True)

    # check for case 1<N<4 or all identical values
    if len(idxs) <= 4 or idxs[0] == idxs[-1]:
        left = []
        right = [1]
        d = 0.0
        return d if just_dip else (d, (None, idxs, left, None, right, None), (None, None, None))

    hist_cumsum = np.cumsum(histogram, dtype=int)
    cdf = np.asarray(hist_cumsum / hist_cumsum[-1], dtype=float)

    work_idxs = np.asarray(idxs, dtype=float)
    work_histogram = np.asarray(histogram, dtype=float) / np.sum(histogram)
    work_cdf = cdf

    D = 0
    left = [0]
    right = [1]

    cumulative_xl = 0
    modalTriangle_i1 = None
    modalTriangle_i2 = None
    modalTriangle_i3 = None
    while True:
        left_part, left_touchpoints = _gcm_(work_cdf - work_histogram, work_idxs)
        right_part, right_touchpoints = _lcm_(work_cdf, work_idxs)

        d_left, left_diffs = _touch_diffs_(left_part,
                                           right_part, left_touchpoints)
        d_right, right_diffs = _touch_diffs_(left_part,
                                             right_part, right_touchpoints)
        if d_right > d_left:
            xr = right_touchpoints[d_right == right_diffs][-1]
            xl = left_touchpoints[left_touchpoints <= xr][-1]
            d = d_right
        else:
            xl = left_touchpoints[d_left == left_diffs][0]
            xr = right_touchpoints[right_touchpoints >= xl][0]
            d = d_left

        left_diff_values = np.abs(left_part[:xl + 1] - work_cdf[:xl + 1])
        arg_left_diff = np.argmax(left_diff_values)
        right_diff_values = np.abs(right_part[xr:]
                                   - work_cdf[xr:]
                                   + work_histogram[xr:])
        arg_right_diff = np.argmax(right_diff_values)
        # Get modal triangle values
        if not just_dip and max(left_diff_values[arg_left_diff], right_diff_values[arg_right_diff]) > D:
            if left_diff_values[arg_left_diff] > right_diff_values[arg_right_diff]:
                cumulative_touchpoints = left_touchpoints + cumulative_xl
                modalTriangle_i2 = arg_left_diff + cumulative_xl
                modalLeft = True
            else:
                cumulative_touchpoints = right_touchpoints + cumulative_xl
                modalTriangle_i2 = arg_right_diff + cumulative_xl + xr
                modalLeft = False
            cumulative_smaller = cumulative_touchpoints[cumulative_touchpoints < modalTriangle_i2]
            modalTriangle_i1 = max(cumulative_smaller) if len(cumulative_smaller) != 0 else None
            cumulative_larger = cumulative_touchpoints[cumulative_touchpoints > modalTriangle_i2]
            modalTriangle_i3 = min(cumulative_larger) if len(cumulative_larger) != 0 else None
            # Final modal triangle
            if modalTriangle_i1 is not None:
                modalTriangle_i1 = hist_cumsum[modalTriangle_i1] - 1 if modalLeft else hist_cumsum[modalTriangle_i1] - \
                                                                                       histogram[modalTriangle_i1]
            modalTriangle_i2 = hist_cumsum[modalTriangle_i2] - histogram[modalTriangle_i2]
            if modalTriangle_i3 is not None:
                modalTriangle_i3 = hist_cumsum[modalTriangle_i3] - histogram[modalTriangle_i3] if modalLeft else \
                    hist_cumsum[modalTriangle_i3] - 1

        if d <= D or xr == 0 or xl == len(work_cdf):
            the_dip = max(np.abs(cdf[:len(left)] - left).max(),
                          np.abs(cdf[-len(right) - 1:-1] - right).max())
            if just_dip:
                return the_dip / 2
            else:
                return the_dip / 2, (cdf, idxs, left, left_part, right, right_part), \
                       (modalTriangle_i1, modalTriangle_i2, modalTriangle_i3)
        else:
            D = max(D, left_diff_values[arg_left_diff], right_diff_values[arg_right_diff])

        work_cdf = work_cdf[xl:xr + 1]
        work_idxs = work_idxs[xl:xr + 1]
        work_histogram = work_histogram[xl:xr + 1]

        left[len(left):] = left_part[1:xl + 1]
        right[:0] = right_part[xr:-1]

        cumulative_xl += xl