# =====================================================================
#  Ou tombe, dans la scene 3D, un point donne de la texture du cadran ?
#  On refait la chaine de transformations en calcul formel, pour lever
#  toute ambiguite de signe sur le placement des aiguilles du dos.
#  SageMath — NAS gypaete — 2026-07-29
# =====================================================================

n = var('n')          # cote de la texture, en pixels
span = var('span')    # cote de la texture, en mm, dans la scene
cx3, cy3 = var('cx3 cy3')
col, row = var('col row')   # position dans l'IMAGE (col vers la droite,
                            # row vers le bas, origine en haut a gauche)

print("=" * 70)
print("  Chaine de transformations texture -> scene")
print("=" * 70)

# 1. image_to_array : data[row][col]
# 2. transpose(1,0,2)  ->  T[i][j] = data[j][i], donc i = col, j = row
i_ = col
j_ = row
print("apres transposition :  i = %s , j = %s" % (i_, j_))

# 3. flip eventuel : data[::-1] inverse la PREMIERE dimension, donc i
i_flip = (n - 1) - i_
print("apres flip (dos)    :  i = %s" % i_flip)

# 4. GLImageItem place data[i][j] au point local (x=i, y=j)
# 5. matrice : translate(cx3,cy3,z) . scale(span/n, span/n) . translate(-n/2,-n/2)
def to_scene(i, j):
    X = cx3 + (i - n/2) * span/n
    Y = cy3 + (j - n/2) * span/n
    return X, Y

X_face, Y_face = to_scene(i_, j_)
X_dos, Y_dos = to_scene(i_flip, j_)
print()
print("FACE AVANT : X = %s" % X_face.simplify_full())
print("             Y = %s" % Y_face.simplify_full())
print("FACE DOS   : X = %s" % X_dos.simplify_full())
print("             Y = %s" % Y_dos.simplify_full())

print()
print("=" * 70)
print("  Application aux deux spirales du dos")
print("=" * 70)
# positions dans la texture, en fraction du cote (cf. dialface.paint_back_dial)
subs_num = {n: 1600, span: 250, cx3: 26.5, cy3: -15.9}
for nom, fx, fy in (("metonique", 0.5, 0.30), ("saros", 0.5, 0.72)):
    Xn = X_dos.subs(col == fx*n, row == fy*n).subs(subs_num)
    Yn = Y_dos.subs(col == fx*n, row == fy*n).subs(subs_num)
    print("  %-10s fraction (%.2f, %.2f) -> X = %s mm , Y = %s mm"
          % (nom, fx, fy, RealField(30)(Xn), RealField(30)(Yn)))

print()
print("  Ecart entre les deux centres (doit valoir span*(0.72-0.30)) :")
Y1 = Y_dos.subs(col == 0.5*n, row == 0.30*n).subs(subs_num)
Y2 = Y_dos.subs(col == 0.5*n, row == 0.72*n).subs(subs_num)
print("     %s mm   attendu %s mm" % (RealField(30)(Y2 - Y1), 250*(0.72-0.30)))

print()
print("  Ce que le code utilisait (layout.py) :")
print("     metonique : Y = cy + span*(0.5 - 0.30) = %s" % (-15.9 + 250*0.20))
print("     saros     : Y = cy + span*(0.5 - 0.72) = %s" % (-15.9 - 250*0.22))
print("  -> les deux signes sont INVERSES par rapport au calcul ci-dessus.")
