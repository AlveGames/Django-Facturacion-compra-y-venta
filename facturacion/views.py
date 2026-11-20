from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin      # exige sesión
from django.contrib.messages.views import SuccessMessageMixin  # mensaje de éxito automático
from django.db import transaction   
from django.db.models import ProtectedError, Q
from django.http import HttpResponseRedirect
from django.shortcuts import redirect,render, get_object_or_404 
from django.urls import reverse,reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView   # las 5 genéricas

from .forms import CategoriaForm, ClienteForm, DetalleVentaFormSet, MarcaForm, PerfilForm, ProductoForm, ProveedorForm, VentaForm
from .mixins import UsuarioRegistroMixin
from .models import Categoria, Cliente, Marca, Perfil, Producto, Proveedor, Venta, DetalleVenta  ,TipoPago, IVA_TARIFA  # Nuestro modelo


# =====================================================================
# MARCAS · Vistas Basadas en Funciones (VBF)
# =====================================================================

def marca_lista(request):                                  # READ: muestra todas las marcas
    q = request.GET.get("q", "") #                         # 1. Leemos el buscador: /facturacion/marcas/?q=sam (si no hay, queda "")
    marcas = Marca.objects.all()                          # 2. Pedimos todas las marcas a la base de datos

    if q:                                                  # 3. Si el usuario escribió algo en el buscador...
        marcas = marcas.filter(nombre__icontains=q)        #    ...dejamos solo las que contienen ese texto

    contexto = {                                           # 4. Datos que enviamos al template
        "titulo": "Marcas",                                #    → {{ titulo }}
        "marcas": marcas,                                  #    → {% for marca in marcas %}
        "q": q,                                            #    → para que el buscador no se borre
    }
    return render(request, "facturacion/marca_lista.html", contexto)   # 5. Mostramos la página

def marca_crear(request):                                  # CREATE: crear una marca nueva

    if request.method == "POST":                           # ¿El usuario presionó "Guardar"? (llegó por POST)
        form = MarcaForm(request.POST)                     # 1. Llenamos el formulario con lo que escribió
        if form.is_valid():                                # 2. ¿Los datos están bien? (obligatorios, únicos, clean_nombre)
            marca = form.save()                            # 3. Guardamos en la base de datos (save devuelve la marca)
            messages.success(request, f"Marca «{marca.nombre}» creada correctamente.")   # 4. Mensaje verde
            return redirect("facturacion:marca_lista")     # 5. Vamos a la lista. Así, si recarga, no se guarda dos veces
        # Si NO es válido, no entra al if: baja hasta el render y muestra el formulario CON errores

    else:                                                  # Si llegó por GET (solo abrió la página)...
        form = MarcaForm()                                 # ...creamos un formulario vacío

    contexto = {                                           # Datos para el template
        "titulo": "Nueva marca",                           # Título de la página
        "form": form,                                      # El formulario (vacío o con errores)
        "boton": "Guardar",                                # Texto del botón
    }
    return render(request, "facturacion/marca_form.html", contexto)



def marca_editar(request, pk):                             # UPDATE. pk llega desde la URL: /marcas/editar/3/ → pk=3
    marca = get_object_or_404(Marca, pk=pk)   
    #marca = Marca.objects.get(id=pk)             # 1. Buscamos la marca. Si no existe → página 404

    if request.method == "POST":                           # 2. ¿Presionó "Actualizar"?
        form = MarcaForm(request.POST, instance=marca)     #    Datos nuevos + la marca que vamos a cambiar
        if form.is_valid():                                #    ¿Están bien?
            form.save()                                    #    Actualiza (UPDATE), no crea una nueva
            messages.success(request, f"Marca «{marca.nombre}» actualizada.")
            return redirect("facturacion:marca_lista")     #    Volvemos a la lista
    else:                                                  # 3. Llegó por GET...
        form = MarcaForm(instance=marca)                   #    ...formulario lleno con los datos actuales

    contexto = {
        "titulo": f"Editar marca: {marca.nombre}",
        "form": form,
        "boton": "Actualizar",
    }
    return render(request, "facturacion/marca_form.html", contexto)   # ¡El mismo template de crear!



def marca_eliminar(request, pk):                           # DELETE
    marca = get_object_or_404(Marca, pk=pk)                # Buscamos la marca o mostramos 404

    if request.method == "POST":                           # ¿Presionó "Sí, eliminar"?
        try:                                               # Intentamos borrar...
            nombre = marca.nombre                          # Guardamos el nombre para el mensaje
            marca.delete()                                 # DELETE en la base de datos
            messages.success(request, f"Marca «{nombre}» eliminada.")
        except ProtectedError:                             # ...si tiene productos, PROTECT no deja borrarla
            messages.error(request, f"No se puede eliminar «{marca.nombre}» porque tiene productos. Desactívala en su lugar.")
        return redirect("facturacion:marca_lista")         # En los dos casos volvemos a la lista

    # Si llegó por GET: mostramos la pregunta "¿Seguro?"
    contexto = {"titulo": "Eliminar marca", "marca": marca}
    return render(request, "facturacion/marca_eliminar.html", contexto)

class ProductoListView(LoginRequiredMixin, ListView):     # LISTAR
    model = Producto                                       # ¿qué tabla?
    template_name = "facturacion/producto_lista.html"      # ¿qué HTML?
    context_object_name = "productos"                      # nombre de la lista en el HTML
    paginate_by = 5                                        # 5 por página → envía page_obj
    extra_context = {"titulo": "Productos"}                # datos fijos extra para el HTML

    def get_queryset(self):                                # ¿QUÉ registros se muestran?
        productos = super().get_queryset()                 # lo normal: Producto.objects.all()
        productos = productos.select_related("marca").prefetch_related("categorias")   # menos consultas
        q = self.request.GET.get("q", "")                  # buscador: ?q=galaxy
        if q:
            productos = productos.filter(nombre__icontains=q)
        return productos

    def get_context_data(self, **kwargs):                  # ¿qué datos EXTRA recibe el HTML?
        contexto = super().get_context_data(**kwargs)      # lo que ListView ya armó
        contexto["q"] = self.request.GET.get("q", "")      # + lo buscado
        return contexto


class ProductoCreateView(LoginRequiredMixin, UsuarioRegistroMixin, SuccessMessageMixin, CreateView):   # CREAR
    model = Producto
    form_class = ProductoForm                              # nuestro formulario
    template_name = "facturacion/producto_form.html"
    success_url = reverse_lazy("facturacion:producto_lista")   # a dónde ir al guardar
    success_message = "Producto «%(nombre)s» creado."      # %(nombre)s = el campo nombre del formulario
    extra_context = {"titulo": "Nuevo producto", "boton": "Guardar"}

class ProductoUpdateView(LoginRequiredMixin, UsuarioRegistroMixin, SuccessMessageMixin, UpdateView):   # EDITAR
    model = Producto
    form_class = ProductoForm
    template_name = "facturacion/producto_form.html"       # el mismo template de crear
    success_url = reverse_lazy("facturacion:producto_lista")
    success_message = "Producto «%(nombre)s» actualizado."
    extra_context = {"titulo": "Editar producto", "boton": "Actualizar"}

    def form_invalid(self, form):                          # cuando hay errores (POST inválido)
        messages.error(self.request, "Revisa los campos marcados en rojo.")
        return super().form_invalid(form)                  # vuelve a mostrar el formulario

class ProductoDetailView(LoginRequiredMixin, DetailView):  # VER UNO
    model = Producto
    template_name = "facturacion/producto_detalle.html"
    context_object_name = "producto"

class ProductoDeleteView(LoginRequiredMixin, DeleteView):  # ELIMINAR
    model = Producto
    template_name = "facturacion/producto_eliminar.html"
    context_object_name = "producto"
    success_url = reverse_lazy("facturacion:producto_lista")

    def form_valid(self, form):                            # se ejecuta al confirmar (POST)
        nombre = self.object.nombre                        # self.object = el producto a eliminar
        try:
            respuesta = super().form_valid(form)           # DELETE + redirect
        except ProtectedError:                             # ya está en una venta o compra (PROTECT)
            messages.error(self.request, f"No se puede eliminar «{nombre}»: ya tiene ventas o compras. Desactívalo.")
            return redirect("facturacion:producto_lista")
        messages.success(self.request, f"Producto «{nombre}» eliminado.")
        return respuesta




# =====================================================================
# TAREA 1 · MARCAS · Vistas Basadas en Clases (VBC)
# Base: Productos (4.2 a 4.6). Todas llevan LoginRequiredMixin PRIMERO.
# =====================================================================

class MarcaListView(LoginRequiredMixin, ListView):        # LISTAR · solo GET
    model = Marca                                          # ¿qué tabla? facturacion_marca
    template_name = "facturacion/marca_lista.html"         # ¿qué HTML? (el mismo de antes)
    context_object_name = "marcas"                         # en el HTML: {% for marca in marcas %}
    extra_context = {"titulo": "Marcas"}                   # dato fijo → {{ titulo }}

    def get_queryset(self):                                # ¿QUÉ registros se muestran?
        marcas = super().get_queryset()                    # lo normal: Marca.objects.all() (A → Z por el Meta)
        q = self.request.GET.get("q", "")                  # GET: lo escrito en el buscador (?q=sam)
        if q:                                              # si buscó algo...
            marcas = marcas.filter(nombre__icontains=q)    # ...solo las que contienen ese texto
        return marcas

    def get_context_data(self, **kwargs):                  # ¿qué datos EXTRA recibe el HTML?
        contexto = super().get_context_data(**kwargs)      # lo que ListView ya armó (marcas, titulo)
        contexto["q"] = self.request.GET.get("q", "")      # + lo buscado, para que el buscador no se borre
        return contexto


class MarcaCreateView(LoginRequiredMixin, UsuarioRegistroMixin, SuccessMessageMixin, CreateView):   # CREAR
    # GET: muestra MarcaForm vacío · POST: valida → UsuarioRegistroMixin pone user → guarda → redirige
    model = Marca
    form_class = MarcaForm                                 # nuestro formulario (con clean_nombre)
    template_name = "facturacion/marca_form.html"
    success_url = reverse_lazy("facturacion:marca_lista")  # reverse_lazy: la URL se calcula cuando se usa
    success_message = "Marca «%(nombre)s» creada."         # mensaje verde. %(nombre)s = el campo nombre
    extra_context = {"titulo": "Nueva marca", "boton": "Guardar"}


class MarcaUpdateView(LoginRequiredMixin, UsuarioRegistroMixin, SuccessMessageMixin, UpdateView):   # EDITAR
    # GET: busca la marca por el pk de la URL y muestra el formulario LLENO · POST: valida y hace UPDATE
    model = Marca
    form_class = MarcaForm
    template_name = "facturacion/marca_form.html"          # el mismo template de crear
    success_url = reverse_lazy("facturacion:marca_lista")
    success_message = "Marca «%(nombre)s» actualizada."
    extra_context = {"titulo": "Editar marca", "boton": "Actualizar"}


class MarcaDeleteView(LoginRequiredMixin, DeleteView):    # ELIMINAR · GET pregunta, POST borra
    model = Marca
    template_name = "facturacion/marca_eliminar.html"
    context_object_name = "marca"                          # en el HTML: {{ marca.nombre }}
    success_url = reverse_lazy("facturacion:marca_lista")

    def form_valid(self, form):                            # se ejecuta al confirmar (POST)
        nombre = self.object.nombre                        # self.object = la marca a eliminar
        try:
            respuesta = super().form_valid(form)           # DELETE + redirect
        except ProtectedError:                             # Producto.marca usa PROTECT: si tiene productos, no se borra
            messages.error(self.request, f"No se puede eliminar «{nombre}»: tiene productos. Desactívala en su lugar.")
            return redirect("facturacion:marca_lista")
        messages.success(self.request, f"Marca «{nombre}» eliminada.")
        return respuesta





# =====================================================================
# TAREA 2 · CATEGORÍAS · VBC (copia de Marcas)
# =====================================================================

class CategoriaListView(LoginRequiredMixin, ListView):    # LISTAR · solo GET
    model = Categoria
    template_name = "facturacion/categoria_lista.html"
    context_object_name = "categorias"                     # en el HTML: {% for categoria in categorias %}
    extra_context = {"titulo": "Categorías"}

    def get_queryset(self):                                # ¿QUÉ registros se muestran?
        categorias = super().get_queryset()
        categorias = categorias.prefetch_related("productos")   # N:M: trae los productos en UNA consulta extra
        q = self.request.GET.get("q", "")                  # buscador: ?q=lac
        if q:
            categorias = categorias.filter(nombre__icontains=q)
        return categorias

    def get_context_data(self, **kwargs):                  # + lo buscado, para que el buscador no se borre
        contexto = super().get_context_data(**kwargs)
        contexto["q"] = self.request.GET.get("q", "")
        return contexto


class CategoriaCreateView(LoginRequiredMixin, UsuarioRegistroMixin, SuccessMessageMixin, CreateView):   # CREAR
    model = Categoria
    form_class = CategoriaForm
    template_name = "facturacion/categoria_form.html"
    success_url = reverse_lazy("facturacion:categoria_lista")
    success_message = "Categoría «%(nombre)s» creada."
    extra_context = {"titulo": "Nueva categoría", "boton": "Guardar"}


class CategoriaUpdateView(LoginRequiredMixin, UsuarioRegistroMixin, SuccessMessageMixin, UpdateView):   # EDITAR
    model = Categoria
    form_class = CategoriaForm
    template_name = "facturacion/categoria_form.html"      # el mismo de crear
    success_url = reverse_lazy("facturacion:categoria_lista")
    success_message = "Categoría «%(nombre)s» actualizada."
    extra_context = {"titulo": "Editar categoría", "boton": "Actualizar"}


class CategoriaDeleteView(LoginRequiredMixin, DeleteView):    # ELIMINAR
    # SIN try/except: Producto.categorias es N:M, así que solo se borran los pares de la tabla
    # intermedia (facturacion_producto_categorias). Los productos siguen existiendo.
    model = Categoria
    template_name = "facturacion/categoria_eliminar.html"
    context_object_name = "categoria"
    success_url = reverse_lazy("facturacion:categoria_lista")

    def form_valid(self, form):                            # solo para el mensaje verde
        messages.success(self.request, f"Categoría «{self.object.nombre}» eliminada.")
        return super().form_valid(form)                    # DELETE + redirect


# =====================================================================
# TAREA 3 · CLIENTES · VBC (base: Productos + el buscador con Q)
# =====================================================================

class ClienteListView(LoginRequiredMixin, ListView):      # LISTAR · paginado y con buscador
    model = Cliente
    template_name = "facturacion/cliente_lista.html"
    context_object_name = "clientes"
    paginate_by = 5                                        # 5 por página → envía page_obj al HTML
    extra_context = {"titulo": "Clientes"}

    def get_queryset(self):
        clientes = super().get_queryset()                  # ordenados por apellidos y nombres (Meta)
        q = self.request.GET.get("q", "")
        if q:
            # Q(...) | Q(...) = "esto O aquello" → WHERE apellidos LIKE '%q%' OR cedula LIKE '%q%'
            clientes = clientes.filter(Q(apellidos__icontains=q) | Q(cedula__icontains=q))
        return clientes

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["q"] = self.request.GET.get("q", "")      # para el buscador y los enlaces de página
        return contexto


class ClienteCreateView(LoginRequiredMixin, UsuarioRegistroMixin, SuccessMessageMixin, CreateView):   # CREAR
    model = Cliente
    form_class = ClienteForm                               # con clean_cedula
    template_name = "facturacion/cliente_form.html"
    success_url = reverse_lazy("facturacion:cliente_lista")
    success_message = "Cliente «%(apellidos)s %(nombres)s» creado."   # usa dos campos del formulario
    extra_context = {"titulo": "Nuevo cliente", "boton": "Guardar"}

    def form_invalid(self, form):                          # POST con errores: mensaje rojo + formulario con errores
        messages.error(self.request, "Revisa los campos marcados en rojo.")
        return super().form_invalid(form)


class ClienteUpdateView(LoginRequiredMixin, UsuarioRegistroMixin, SuccessMessageMixin, UpdateView):   # EDITAR
    model = Cliente
    form_class = ClienteForm
    template_name = "facturacion/cliente_form.html"
    success_url = reverse_lazy("facturacion:cliente_lista")
    success_message = "Cliente «%(apellidos)s %(nombres)s» actualizado."
    extra_context = {"titulo": "Editar cliente", "boton": "Actualizar"}

    def form_invalid(self, form):
        messages.error(self.request, "Revisa los campos marcados en rojo.")
        return super().form_invalid(form)


class ClienteDetailView(LoginRequiredMixin, DetailView):  # VER UNO: sus datos + sus ventas
    model = Cliente
    template_name = "facturacion/cliente_detalle.html"
    context_object_name = "cliente"                        # en el HTML: cliente.ventas.all (related_name="ventas")


class ClienteDeleteView(LoginRequiredMixin, DeleteView):  # ELIMINAR
    model = Cliente
    template_name = "facturacion/cliente_eliminar.html"
    context_object_name = "cliente"
    success_url = reverse_lazy("facturacion:cliente_lista")

    def form_valid(self, form):
        nombre = str(self.object)                          # "Pérez Ana" (el __str__ del modelo)
        try:
            respuesta = super().form_valid(form)           # DELETE + redirect
        except ProtectedError:                             # Venta.cliente usa PROTECT: un cliente con ventas no se borra
            messages.error(self.request, f"No se puede eliminar a «{nombre}»: tiene ventas registradas.")
            return redirect("facturacion:cliente_lista")
        messages.success(self.request, f"Cliente «{nombre}» eliminado.")
        return respuesta





# =====================================================================
# TAREA 4 · PROVEEDORES · VBC (base: Clientes + la foto de Productos)
# =====================================================================

class ProveedorListView(LoginRequiredMixin, ListView):    # LISTAR · con miniatura del logo
    model = Proveedor
    template_name = "facturacion/proveedor_lista.html"
    context_object_name = "proveedores"
    paginate_by = 5
    extra_context = {"titulo": "Proveedores"}

    def get_queryset(self):
        proveedores = super().get_queryset()
        q = self.request.GET.get("q", "")
        if q:                                              # busca por nombre, apellido O RUC
            proveedores = proveedores.filter(
                Q(nombre__icontains=q) | Q(apellido__icontains=q) | Q(ruc__icontains=q)
            )
        return proveedores

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["q"] = self.request.GET.get("q", "")
        return contexto


class ProveedorCreateView(LoginRequiredMixin, UsuarioRegistroMixin, SuccessMessageMixin, CreateView):   # CREAR
    # La VBC pasa request.FILES al formulario sola: solo falta el enctype en el template
    model = Proveedor
    form_class = ProveedorForm
    template_name = "facturacion/proveedor_form.html"
    success_url = reverse_lazy("facturacion:proveedor_lista")
    success_message = "Proveedor «%(nombre)s %(apellido)s» creado."
    extra_context = {"titulo": "Nuevo proveedor", "boton": "Guardar"}

    def form_invalid(self, form):
        messages.error(self.request, "Revisa los campos marcados en rojo.")
        return super().form_invalid(form)


class ProveedorUpdateView(LoginRequiredMixin, UsuarioRegistroMixin, SuccessMessageMixin, UpdateView):   # EDITAR
    model = Proveedor
    form_class = ProveedorForm
    template_name = "facturacion/proveedor_form.html"      # muestra el logo actual y deja cambiarlo o quitarlo
    success_url = reverse_lazy("facturacion:proveedor_lista")
    success_message = "Proveedor «%(nombre)s %(apellido)s» actualizado."
    extra_context = {"titulo": "Editar proveedor", "boton": "Actualizar"}

    def form_invalid(self, form):
        messages.error(self.request, "Revisa los campos marcados en rojo.")
        return super().form_invalid(form)


class ProveedorDeleteView(LoginRequiredMixin, DeleteView):    # ELIMINAR
    model = Proveedor
    template_name = "facturacion/proveedor_eliminar.html"
    context_object_name = "proveedor"
    success_url = reverse_lazy("facturacion:proveedor_lista")

    def form_valid(self, form):
        nombre = str(self.object)
        try:
            respuesta = super().form_valid(form)
        except ProtectedError:                             # Compra.proveedor usa PROTECT: con compras no se borra
            messages.error(self.request, f"No se puede eliminar a «{nombre}»: tiene compras registradas.")
            return redirect("facturacion:proveedor_lista")
        messages.success(self.request, f"Proveedor «{nombre}» eliminado.")
        return respuesta


# =====================================================================
# RETO · MI PERFIL con UpdateView (sin <int:pk> en la URL)
# =====================================================================

class MiPerfilView(LoginRequiredMixin, UsuarioRegistroMixin, SuccessMessageMixin, UpdateView):
    model = Perfil
    form_class = PerfilForm
    template_name = "facturacion/mi_perfil.html"
    success_url = reverse_lazy("facturacion:mi_perfil")    # vuelve a la MISMA página
    success_message = "Tu perfil se actualizó correctamente."
    extra_context = {"titulo": "Mi perfil"}

    def get_object(self, queryset=None):                   # en vez de buscar por pk...
        # ...el perfil del usuario conectado. Si no existe, lo crea vacío (creado = True)
        perfil, creado = Perfil.objects.get_or_create(usuario=self.request.user)
        return perfil




    







class VentaListView(LoginRequiredMixin, ListView):
    model = Venta
    template_name = "facturacion/venta_lista.html"
    context_object_name = "ventas"
    paginate_by = 10
    extra_context = {"titulo": "Ventas", "tipos_pago": TipoPago.choices}   # opciones para el filtro

    def get_queryset(self):
        ventas = super().get_queryset().select_related("cliente")   # trae el cliente en el mismo JOIN
        q = self.request.GET.get("q", "")
        tipo = self.request.GET.get("tipo_pago", "")
        if q:   # Q(...) | Q(...) = condición con OR: por apellido O por cédula
            ventas = ventas.filter(Q(cliente__apellidos__icontains=q) | Q(cliente__cedula__icontains=q))
        if tipo:
            ventas = ventas.filter(tipo_pago=tipo)
        return ventas

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["q"] = self.request.GET.get("q", "")
        contexto["tipo_pago"] = self.request.GET.get("tipo_pago", "")
        return contexto
    









class VentaDetallesMixin:
    """Lo que COMPARTEN crear y editar una venta: cabecera (form) + filas (formset)."""
    model = Venta
    form_class = VentaForm
    template_name = "facturacion/venta_form.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)      # trae "form" (la cabecera)
        if "detalles" not in contexto:                     # en GET el formset todavía no existe...
            contexto["detalles"] = DetalleVentaFormSet(instance=self.object)   # ...lo creamos (vacío o lleno)
        return contexto

    def post(self, request, *args, **kwargs):              # REEMPLAZA el post() normal de la vista
        form = self.get_form()                             # 1. cabecera con request.POST
        detalles = DetalleVentaFormSet(request.POST, instance=self.object)   # 2. filas con request.POST
        if form.is_valid() and detalles.is_valid():        # 3. ¿las DOS partes están bien?
            return self.form_valid(form, detalles)
        return self.form_invalid(form, detalles)

    def form_valid(self, form, detalles):
        with transaction.atomic():                         # TODO o NADA: si algo falla, se deshace todo
            if self.object:                                # al EDITAR: devolver lo que la venta tenía
                self.object.devolver_stock()
            form.instance.user = self.request.user
            self.object = form.save()                      # INSERT o UPDATE de la cabecera
            self.guardar_detalles(detalles)                # INSERT / UPDATE / DELETE de las filas
            self.object.descontar_stock()                  # saca de bodega lo vendido
            self.object.calcular_totales()                 # subtotal, IVA y total
        messages.success(self.request, f"{self.object} guardada. Total: ${self.object.total}")
        return HttpResponseRedirect(self.get_success_url())

    def guardar_detalles(self, detalles):
        detalles.instance = self.object                    # las filas pertenecen a ESTA venta
        filas = detalles.save(commit=False)                # objetos nuevos o cambiados, SIN guardar todavía
        for fila in detalles.deleted_objects:              # filas con la casilla "Quitar"
            fila.delete()
        cambio_producto = {obj.pk for obj, campos in detalles.changed_objects if "producto" in campos}
        for fila in filas:
            if fila.pk is None or fila.pk in cambio_producto:   # fila nueva o con otro producto...
                fila.precio = fila.producto.precio              # ...toma el precio ACTUAL del producto
            fila.user = self.request.user
            fila.save()

    def form_invalid(self, form, detalles):
        messages.error(self.request, "Revisa los datos de la venta.")
        # volvemos a dibujar la página con la cabecera Y las filas, con sus errores
        return self.render_to_response(self.get_context_data(form=form, detalles=detalles))

    def get_success_url(self):
        return reverse("facturacion:venta_detalle", kwargs={"pk": self.object.pk})   # a la factura




class VentaCreateView(LoginRequiredMixin, VentaDetallesMixin, CreateView):   # CREAR
    extra_context = {"titulo": "Nueva venta", "boton": "Guardar venta"}

    def post(self, request, *args, **kwargs):
        self.object = None                                 # CreateView: aún no hay venta
        return super().post(request, *args, **kwargs)      # sigue al post() del mixin



class VentaDetailView(LoginRequiredMixin, DetailView):     # VER (la factura)
    model = Venta
    template_name = "facturacion/venta_detalle.html"
    context_object_name = "venta"

    def get_queryset(self):
        return super().get_queryset().select_related("cliente", "user").prefetch_related("detalles__producto")

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["iva_porcentaje"] = IVA_TARIFA * 100      # 15
        return contexto




    
class VentaUpdateView(LoginRequiredMixin, VentaDetallesMixin, UpdateView):   # EDITAR
    extra_context = {"titulo": "Editar venta", "boton": "Actualizar venta"}

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()                    # UpdateView: la venta del <int:pk>
        return super().post(request, *args, **kwargs)




class VentaDeleteView(LoginRequiredMixin, DeleteView):     # ELIMINAR
    model = Venta
    template_name = "facturacion/venta_eliminar.html"
    context_object_name = "venta"
    success_url = reverse_lazy("facturacion:venta_lista")

    def form_valid(self, form):
        with transaction.atomic():
            self.object.devolver_stock()                   # 1. los productos regresan a la bodega
            respuesta = super().form_valid(form)           # 2. DELETE de la venta (CASCADE borra sus detalles)
        messages.success(self.request, "Venta eliminada y stock devuelto.")
        return respuesta