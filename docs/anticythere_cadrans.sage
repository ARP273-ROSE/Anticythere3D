# =====================================================================
#  Placement des cadrans : geometrie complete, en millimetres.
#  On verifie que chaque anneau, chaque spirale et chaque aiguille tombe
#  la ou il faut, et que tout tient dans le boitier.
#  SageMath — NAS gypaete — 2026-07-29
# =====================================================================
R = RealField(40)

def titre(t):
    print("\n" + "=" * 72)
    print("  " + t)
    print("=" * 72)

# --- donnees de l'implantation (layout.py) ---------------------------
MODULE = 1.0
CASE_W, CASE_H = R('306.0'), R('285.0')
CASE_CX, CASE_CY = R('26.5'), R('-15.9')

# --- fractions du trace, telles que codees dans dialface.py -----------
# face avant, rapportees a R = span/2
F_CAL_OUT, F_CAL_IN = R(1.0), R('0.845')
F_ZOD_OUT, F_ZOD_IN = R('0.825'), R('0.63')
F_FACE = R('0.61')
# face arriere, rapportees au cote de la texture
FY_METON, FY_SAROS = R('0.30'), R('0.72')
FR_METON, FR_SAROS = R('0.20'), R('0.185')
FR_METON_IN, FR_SAROS_IN = R('0.055'), R('0.050')
FX_GAMES, FY_GAMES, FR_GAMES = R('0.185'), R('0.30'), R('0.062')
FX_CALL, FY_CALL, FR_CALL = R('0.815'), R('0.30'), R('0.052')
FX_EXEL, FY_EXEL, FR_EXEL = R('0.5'), R('0.945'), R('0.048')

titre("1. CADRAN AVANT — quel diametre lui donner ?")
# Il doit couvrir l'anneau du zodiaque sans deborder du boitier, et
# l'aiguille du Soleil doit pointer DANS l'anneau du zodiaque.
for span in (R(230), R(244), R(250), R(260)):
    Rr = span/2
    print("  span = %s mm  ->  rayon %s" % (span, Rr))
    print("      calendrier  : %s .. %s mm" % (R(F_CAL_IN*Rr), R(F_CAL_OUT*Rr)))
    print("      zodiaque    : %s .. %s mm" % (R(F_ZOD_IN*Rr), R(F_ZOD_OUT*Rr)))
    print("      plage libre : jusqu'a %s mm" % R(F_FACE*Rr))

titre("2. CONTRAINTES DU CADRAN AVANT")
# Le cadran est centre sur l'arbre b, en (0,0) ; le boitier est centre en
# (CASE_CX, CASE_CY). Il ne doit pas deborder.
x0, x1 = CASE_CX - CASE_W/2, CASE_CX + CASE_W/2
y0, y1 = CASE_CY - CASE_H/2, CASE_CY + CASE_H/2
print("  boitier : x de %s a %s , y de %s a %s" % (R(x0), R(x1), R(y0), R(y1)))
marge = min(abs(x0), abs(x1), abs(y0), abs(y1))
print("  le cadran avant est centre en (0,0) : rayon maximal = %s mm" % R(marge))
span_max = 2*marge
print("  -> span maximal = %s mm" % R(span_max))
span_front = R(244)
Rf = span_front/2
print("  span retenu = %s mm" % span_front)
r_zod_mid = (F_ZOD_IN + F_ZOD_OUT)/2 * Rf
print("  milieu de l'anneau du zodiaque = %s mm" % R(r_zod_mid))
print("  -> aiguille du Soleil : %s mm (pointe au milieu du zodiaque)"
      % R(F_ZOD_OUT*Rf - 3))
print("  -> aiguille de la Lune : %s mm" % R(r_zod_mid))

titre("3. CADRAN ARRIERE — position des deux spirales")
span_back = R(250)
print("  span = %s mm, centre du cadran = (%s, %s)"
      % (span_back, CASE_CX, CASE_CY))
print("  formule verifiee : Y = cy + span*(fy - 1/2)")
for nom, fy, fr, fr_in in (("metonique", FY_METON, FR_METON, FR_METON_IN),
                           ("saros", FY_SAROS, FR_SAROS, FR_SAROS_IN)):
    Y = CASE_CY + span_back*(fy - R(0.5))
    r_out, r_in = span_back*fr, span_back*fr_in
    print("  %-10s centre Y = %8s mm   spirale de %s a %s mm"
          % (nom, R(Y), R(r_in), R(r_out)))
    print("             s'etend de %s a %s mm en Y" % (R(Y - r_out), R(Y + r_out)))

Y_met = CASE_CY + span_back*(FY_METON - R(0.5))
Y_sar = CASE_CY + span_back*(FY_SAROS - R(0.5))
print("\n  ecart entre les deux centres : %s mm" % R(Y_sar - Y_met))
recouvrement = (Y_met + span_back*FR_METON) - (Y_sar - span_back*FR_SAROS)
print("  recouvrement des deux spirales : %s mm  -> %s"
      % (R(recouvrement), "OK" if recouvrement < 0 else "ELLES SE TOUCHENT"))

titre("4. TIENNENT-ILS DANS LE BOITIER ?")
for nom, fx, fy, fr in (("spirale metonique", R(0.5), FY_METON, FR_METON),
                        ("spirale saros", R(0.5), FY_SAROS, FR_SAROS),
                        ("cadran des Jeux", FX_GAMES, FY_GAMES, FR_GAMES),
                        ("cadran callippique", FX_CALL, FY_CALL, FR_CALL),
                        ("cadran exeligmos", FX_EXEL, FY_EXEL, FR_EXEL)):
    X = CASE_CX - span_back*(fx - R(0.5))     # la face arriere est miroitee
    Y = CASE_CY + span_back*(fy - R(0.5))
    r = span_back*fr
    ok = (X - r >= x0) and (X + r <= x1) and (Y - r >= y0) and (Y + r <= y1)
    print("  %-20s centre (%7s, %8s) rayon %6s  -> %s"
          % (nom, R(X), R(Y), R(r), "dans le boitier" if ok else "DEBORDE"))

titre("5. LONGUEUR DES AIGUILLES DU DOS")
for nom, fr, fr_in in (("metonique", FR_METON, FR_METON_IN),
                       ("saros", FR_SAROS, FR_SAROS_IN)):
    r_out = span_back*fr
    print("  %-10s : spirale jusqu'a %s mm -> aiguille de %s mm"
          % (nom, R(r_out), R(r_out*R('1.02'))))

titre("6. SYNTHESE — valeurs a coder")
print("  BACK_DIAL_SPAN   = %s" % span_back)
print("  FRONT_DIAL_SPAN  = %s   (au lieu de 250 : le cadran debordait)"
      % span_front)
print("  METONIC_CENTER   = (CASE_CX, CASE_CY %+s)" % R(span_back*(FY_METON-R(0.5))))
print("  SAROS_CENTER     = (CASE_CX, CASE_CY %+s)" % R(span_back*(FY_SAROS-R(0.5))))
print("  METONIC_RADIUS   = %s" % R(span_back*FR_METON))
print("  SAROS_RADIUS     = %s" % R(span_back*FR_SAROS))
print("  aiguille Soleil  = %s mm" % R(F_ZOD_OUT*Rf - 3))
print("  aiguille Lune    = %s mm" % R(r_zod_mid))
