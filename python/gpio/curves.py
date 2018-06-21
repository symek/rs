

class CurveEnum(object):
    HAND_MADE_GAUSS = 
        ((-0.0007715321844443679, 0.008120737969875336),
         (0.1666666865348816, 0.2561919391155243),
         (0.3006516993045807, 0.31754636764526367),
         (0.47332537174224854, 1.0058536529541016),
         (0.5807352662086487, 0.35222336649894714),
         (0.8474814891815186, 0.2615295648574829),
         (1.0, -0.004779990762472153))

    HAND_MADE_EASY_OUT = 
        ((0.00989831704646349, -0.13058727979660034),
        (0.06858249008655548, 0.5122683048248291),
        (0.3006516993045807, 0.31754636764526367),
        (0.47332537174224854, 1.0058536529541016),
        (0.5807352662086487, 0.35222336649894714),
        (0.7727925181388855, 0.2375224083662033),
        (1.0, -0.004779990762472153))
    HAND_MADE_EASY_OUT_FAST_START = 
        ((0.020568164065480232, 0.10948430746793747),
        (0.06858249008655548, 0.5122683048248291),
        (0.23663261532783508, 0.42957979440689087),
        (0.47136929631233215, 1.005751609802246),
        (0.5807352662086487, 0.35222336649894714),
        (0.7781274318695068, 0.30154159665107727),
        (1.0, -0.004779990762472153))
    HAND_MADE_EASY_OUT_FAST_START2 = 
        (0.024404475465416908, 0.3426625430583954),
         (0.06512012332677841, 0.5489551424980164),
         (0.20898208022117615, 0.5190970301628113),
         (0.4342753291130066, 1.2438355684280396),
         (0.6731404662132263, 0.4159507155418396),
         (0.8631468415260315, 0.3128044009208679),
         (1.0205806493759155, -0.02378062531352043))


class Curve(object):
    YP = None
    def __init__(self, range_, order=4, curve=None):
        self.range = range_
        self.order = order
        self.curve = curve

    def easeInOutQuad(self, t):
        """"""
        if t<.5:
            return 2.0*t*t
        else:
            return -1.0+(4.0-2.0*t)*t

    def easeInOutCubic(self, t):
        """"""
        if t<.5:
            return 4*t*t*t
        else:
            return (t-1.0)*(2.0*t-2.0)*(2.0*t-2.0)+1.0

    def easeInOutSine(self, t,b,c,d):
        """"""
        from math import cos, pi
        return -c/2.0 * (cos(pi* t/d) -1.0)+b

    def poly(self, index):
        """ polyfit version which has the same API like above
            functions.
        """
        if not self.YP:
            self.YP = tuple(self.__compute_polyfit(self.range, self.curve, self.order))

        assert len(self.YP) >= index
        return self.YP[index]

    def __compute_polyfit(self, range_, curve=None, order=4):
        """
        """
        from numpy import polyfit, polyval
        if not curve:        
            curve = CurveEnum.HAND_MADE_EASY_OUT_FAST_START2
        X  = [x[0] for x in curve]
        Y  = [y[1] for y in curve]
        step = 1.0/range_
        XP = [x*step for x in range(0,range_)]
        p1 = polyfit(X,Y, order)
        YP = polyval(p1, XP)
        self.YP = YP
        return YP