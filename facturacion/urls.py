from django.urls import path               # path() une una dirección con una vista
from . import views                        # Las vistas de ESTA app (facturacion/views.py)

app_name = "facturacion"                   # "Apellido" de las URLs de esta app. En templates: 'facturacion:marca_lista'

urlpatterns = [
        # ---------- MARCAS: clases (VBC) · Tarea 1 ----------
    path("marcas/", views.MarcaListView.as_view(), name="marca_lista"),                          # .as_view(): obligatorio en clases
    path("marcas/crear/", views.MarcaCreateView.as_view(), name="marca_crear"),
    path("marcas/editar/<int:pk>/", views.MarcaUpdateView.as_view(), name="marca_editar"),       # pk → get_object()
    path("marcas/eliminar/<int:pk>/", views.MarcaDeleteView.as_view(), name="marca_eliminar"),
    
    # ---------- PRODUCTOS: clases (VBC) ----------
    path("productos/", views.ProductoListView.as_view(), name="producto_lista"),   # .as_view(): obligatorio en clases
    path("productos/crear/", views.ProductoCreateView.as_view(), name="producto_crear"),
    path("productos/editar/<int:pk>/", views.ProductoUpdateView.as_view(), name="producto_editar"),   # pk → get_object()
    path("productos/<int:pk>/", views.ProductoDetailView.as_view(), name="producto_detalle"),
    path("productos/eliminar/<int:pk>/", views.ProductoDeleteView.as_view(), name="producto_eliminar"),

]