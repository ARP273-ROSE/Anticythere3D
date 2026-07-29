"""
Quad texturé à coordonnées UV explicites — remplace GLImageItem.

Textured quad with explicit UV coordinates — replaces GLImageItem.

Pourquoi : ``GLImageItem`` transpose l'image en interne avant de l'envoyer à
OpenGL (vu dans son code source : ``data.transpose((1, 0, 2))``), ce qui rend
l'orientation finale difficile à raisonner — et rendait les inscriptions de la
face arrière illisibles, en miroir. Ici, la correspondance est écrite noir sur
blanc : le texel (u, v) va au sommet (x, y) que NOUS choisissons, et le miroir
de la face arrière est un simple échange de coordonnées U.

La chaîne complète est vérifiée en calcul formel dans
``docs/anticythere_texture.sage``.
"""

from __future__ import annotations

import numpy as np
from OpenGL import GL
from pyqtgraph.opengl.GLGraphicsItem import GLGraphicsItem


class TexturedQuadItem(GLGraphicsItem):
    """Un rectangle dans le plan z = 0 de son repère local, portant une image.

    * l'image est fournie en convention habituelle : ``img[row][col]``,
      ``row`` croissant vers le bas ;
    * le quad va de ``(-w/2, -h/2)`` à ``(+w/2, +h/2)`` ;
    * la PREMIÈRE ligne de l'image est affichée en HAUT (+y), comme à l'écran ;
    * ``mirror_x=True`` retourne l'image gauche-droite — c'est ce qu'il faut
      pour une face que l'on regarde par derrière.
    """

    def __init__(self, img_rgba: np.ndarray, width: float, height: float,
                 mirror_x: bool = False, smooth: bool = True,
                 glOptions: str = "translucent", parentItem=None):
        super().__init__(parentItem=parentItem)
        self.setGLOptions(glOptions)
        self._img = np.ascontiguousarray(img_rgba, dtype=np.uint8)
        self._w = float(width)
        self._h = float(height)
        self._mirror = bool(mirror_x)
        self._smooth = bool(smooth)
        self._texture = None
        self._dirty = True

    # ------------------------------------------------------------------ data
    def set_image(self, img_rgba: np.ndarray):
        self._img = np.ascontiguousarray(img_rgba, dtype=np.uint8)
        self._dirty = True
        self.update()

    def _upload(self):
        if self._texture is None:
            self._texture = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self._texture)
        filt = GL.GL_LINEAR if self._smooth else GL.GL_NEAREST
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, filt)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, filt)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S,
                           GL.GL_CLAMP_TO_EDGE)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T,
                           GL.GL_CLAMP_TO_EDGE)
        h, w = self._img.shape[:2]
        # glTexImage2D lit les LIGNES de bas en haut : la ligne 0 du tableau
        # devient v = 0, en BAS de l'espace texture.
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA, w, h, 0,
                        GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, self._img)
        self._dirty = False

    # ---------------------------------------------------------------- render
    def paint(self):
        self.setupGLState()
        if self._dirty:
            self._upload()

        # pyqtgraph ≥ 0.13 ne charge plus les matrices du pipeline fixe :
        # sans ce bloc, les sommets partent directement en espace de clip et
        # le quad remplit l'écran. On pousse la MVP complète en PROJECTION
        # (modelview identité), ce qui revient au même produit.
        mvp = np.array(self.mvpMatrix().data(), dtype=np.float32)
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glPushMatrix()
        GL.glLoadMatrixf(mvp)
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glPushMatrix()
        GL.glLoadIdentity()

        GL.glEnable(GL.GL_TEXTURE_2D)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self._texture)
        GL.glColor4f(1.0, 1.0, 1.0, 1.0)

        hw, hh = self._w / 2.0, self._h / 2.0
        # v = 0 est la ligne 0 du tableau, donc le HAUT de l'image ; on
        # l'attache à +y. u va de gauche (0) à droite (1), inversé si miroir.
        u0, u1 = (1.0, 0.0) if self._mirror else (0.0, 1.0)
        quad = (
            (u0, 0.0, -hw, +hh),      # haut gauche de l'image
            (u1, 0.0, +hw, +hh),      # haut droit
            (u1, 1.0, +hw, -hh),      # bas droit
            (u0, 1.0, -hw, -hh),      # bas gauche
        )
        GL.glBegin(GL.GL_QUADS)
        for u, v, x, y in quad:
            GL.glTexCoord2f(u, v)
            GL.glVertex3f(x, y, 0.0)
        GL.glEnd()
        GL.glDisable(GL.GL_TEXTURE_2D)

        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glPopMatrix()
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glPopMatrix()
