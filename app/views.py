from django.shortcuts import render,redirect
from django.contrib import messages
from .models import *
from django.contrib.auth import authenticate, login, logout,update_session_auth_hash

def home(request):
    products = Product.objects.all()[:3]
    return render(request,'app/home.html',{'products': products})


def cart(request):
    return render(request,'app/cart.html')


"""
def checkout(request):
    countries = [(country.alpha_2, country.name) for country in pycountry.countries]
    user = request.user if request.user.is_authenticated else None



    customer_info = {}
    customer = None
    shipping_data = {}
    shipping_address = None


    if user:
        try:
            customer = Customer.objects.get(user=user)
            customer_info = {
                'full_name': f"{user.first_name} {user.last_name}",
                'email': user.email,
                'mobile': customer.mobile if hasattr(customer, 'mobile') else ''
            }
            last_order = Order.objects.filter(customer=customer, complete=True).order_by('-date_order').first()
            if last_order:
                shipping_address = ShippingAddress.objects.filter(order=last_order).last()
                if shipping_address:
                    shipping_data = {
                        'address': shipping_address.address,
                        'city': shipping_address.city,
                        'state': shipping_address.state,
                        'country': shipping_address.country,
                        'mobile': shipping_address.mobile
                    }
        except Customer.DoesNotExist:
            customer = None
        except Customer.DoesNotExist:
            customer = None

    if request.method == 'POST':
        #  Lấy dữ liệu
        cart_raw = request.POST.get('cart_data', '')
        try:
            cart_data = json.loads(cart_raw) if cart_raw else []
        except json.JSONDecodeError:
            cart_data = []

        coupon_code = request.POST.get('coupon_code', '').strip()
        coupon_code_input = coupon_code
        invalid_coupon = False

        fullname = request.POST.get('c_fullname', '').strip()
        address = request.POST.get('c_address', '').strip()
        country = request.POST.get('c_diff_country', '').strip()
        state = request.POST.get('c_state', '').strip()
        city = request.POST.get('c_city', '').strip()
        email = request.POST.get('c_email_address', '').strip()
        mobile = request.POST.get('c_mobile', '').strip()
        order_note = request.POST.get('c_order_notes', '').strip()
        payment_method = request.POST.get('payment_method', 'cash').strip()

        #Kiểm tra bắt buộc
        if not all([address, city, state, mobile]):
            return redirect('checkout')

        #  Re-use order nếu có
        order = None
        order_id = request.session.get('order_id')
        # Nếu thật sự cần re-use order, chỉ xóa nếu đơn chưa hoàn tất
        if order_id:
            try:
                order = Order.objects.get(id=order_id, complete=False)
            except Order.DoesNotExist:
                order = None
        if not order:
            order = Order.objects.create(
                customer=customer,
                cusnote=order_note
            )
            request.session['order_id'] = order.id

        if coupon_code:
            try:
                coupon = Coupon.objects.get(code=coupon_code, is_active=True)
                order.coupon = coupon
                order.save()
            except Coupon.DoesNotExist:
                invalid_coupon = True

        for item in cart_data:
            try:
                product_id = int(item['id'])
                print(f" Đang xử lý sản phẩm ID: {product_id}")
                product = Product.objects.get(id=product_id)
            except Product.DoesNotExist:
                print(f" Product ID {item['id']} not found, skipping")
                continue

            #  Chỉ tạo OrderItem nếu product hợp lệ
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=item['quantity']
            )
            print(f" Created OrderItem: {product.name} x {item['quantity']}")

        shipping_address, _ = ShippingAddress.objects.update_or_create(
            order=order,
            defaults={
                'customer': customer,
                'address': address,
                'city': city,
                'country': country,
                'mobile': mobile,
                'state': state
            }
        )

        order.payment_method = payment_method
        order.transaction_id = f"MANUAL_{order.id}"
        order.complete = True
        order.save()
        summary, _ = OrderSummary.objects.get_or_create(order=order)
        summary.update_from_order()

        # Điểm thưởng nếu có
        if customer:
            total_items = sum(item.quantity for item in order.orderitem_set.all())
            customer.points += total_items // 5
            customer.save()
        else:
            GuestOrder.objects.update_or_create(
                order=order,
                defaults={
                    'name': fullname,
                    'email': email,
                    'mobile': mobile
                }
            )

        # Xoá session để tránh re-submit
        request.session.pop('order_id', None)
        request.session.pop('cart', None)

        print(" Tổng OrderItem của Order", order.id, ":", order.orderitem_set.count())
        print(" Order marked complete:", order.id)
        print("User:", user)
        print("Customer:", customer)
        print("ShippingAddress:", shipping_address)
        print("ShippingData:", shipping_data)


        return redirect('confirmpayment')

    return render(request, 'app/checkout.html', {
        'countries': countries,
        'customer_info': customer_info,
        'shipping_data': shipping_data,
    })

"""

def get_default_shipping_data(customer):
    last_order = Order.objects.filter(customer=customer, complete=True).order_by('-date_order').first()
    if last_order:
        shipping_address = ShippingAddress.objects.filter(order=last_order).last()
        if shipping_address:
            return {
                'address': shipping_address.address or '',
                'city': shipping_address.city or '',
                'state': shipping_address.state or '',
                'country': shipping_address.country or '',
                'mobile': shipping_address.mobile or ''
            }
    return {}

def create_or_reuse_order(request, customer, order_note):
    order_id = request.session.get('order_id')
    order = None
    if order_id:
        order = Order.objects.filter(id=order_id, complete=False).first()
    if not order:
        order = Order.objects.create(customer=customer, cusnote=order_note)
        request.session['order_id'] = order.id
    return order

def update_shipping_address(order, customer, address, city, state, country, mobile):
    shipping_address, _ = ShippingAddress.objects.update_or_create(
        order=order,
        defaults={
            'customer': customer,
            'address': address,
            'city': city,
            'country': country,
            'mobile': mobile,
            'state': state
        }
    )
    return shipping_address


def checkout(request):
    import pycountry, json
    countries = [(country.alpha_2, country.name) for country in pycountry.countries]
    user = request.user if request.user.is_authenticated else None

    customer_info, customer, shipping_data = {}, None, {}

    if user:
        try:
            customer = Customer.objects.get(user=user)
            customer_info = {
                'full_name': f"{user.first_name} {user.last_name}",
                'email': user.email,
                'mobile': getattr(customer, 'mobile', '')
            }
            shipping_data = get_default_shipping_data(customer)
        except Customer.DoesNotExist:
            customer = None

    if request.method == 'POST':
        cart_data = []
        try:
            cart_data = json.loads(request.POST.get('cart_data', '') or '[]')
        except Exception: pass

        coupon_code = request.POST.get('coupon_code', '').strip()
        invalid_coupon = False

        # Lấy các trường shipping/post
        post_fields = ['c_fullname','c_address','c_diff_country','c_state','c_city','c_email_address','c_mobile','c_order_notes']
        post_vals = [request.POST.get(f, '').strip() for f in post_fields]
        fullname, address, country, state, city, email, mobile, order_note = post_vals
        payment_method = request.POST.get('payment_method', 'cash').strip()

        if not all([address, city, state, mobile]):
            return redirect('checkout')

        order = create_or_reuse_order(request, customer, order_note)

        # Coupon
        if coupon_code:
            try:
                coupon = Coupon.objects.get(code=coupon_code, is_active=True)
                order.coupon = coupon
                order.save()
            except Coupon.DoesNotExist:
                invalid_coupon = True

        # Order items
        for item in cart_data:
            try:
                product_id = int(item['id'])
                print(f" Đang xử lý sản phẩm ID: {product_id}")
                product = Product.objects.get(id=product_id)
            except Product.DoesNotExist:
                print(f" Product ID {item['id']} not found, skipping")
                continue
            #  Chỉ tạo OrderItem nếu product hợp lệ
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=item['quantity']
            )
            print(f" Created OrderItem: {product.name} x {item['quantity']}")

        shipping_address = update_shipping_address(order, customer, address, city, state, country, mobile)

        order.payment_method = payment_method
        order.transaction_id = f"MANUAL_{order.id}"
        order.complete = True
        order.save()

        summary, _ = OrderSummary.objects.get_or_create(order=order)
        summary.update_from_order()

        if customer:
            total_items = sum(item.quantity for item in order.orderitem_set.all())
            customer.points += total_items // 5
            customer.save()
        else:
            GuestOrder.objects.update_or_create(
                order=order, defaults={'name': fullname, 'email': email, 'mobile': mobile}
            )

        request.session.pop('order_id', None)
        request.session.pop('cart', None)

        return redirect('confirmpayment')

    return render(request, 'app/checkout.html', {
        'countries': countries,
        'customer_info': customer_info,
        'shipping_data': shipping_data,
    })




def shop(request):
    products = Product.objects.all()
    return render(request,'app/shop.html',{'products': products})

def service(request):
    products = Product.objects.all()[:3]
    return render(request,'app/service.html',{'products': products})

def pro_detail(request):
    id = request.GET.get('id', '')
    products = Product.objects.filter(id=id) if id else Product.objects.none()
    return render(request, 'app/prodetail.html', {'products' : products})


def search(request):
    searched = ""
    keys = []
    if request.method == "POST":
        searched = request.POST["searched"]
        keys=Product.objects.filter(name__contains= searched)
    return render(request,'app/search.html',{'searched':searched,'keys':keys})

def blog(request):
    return render(request,'app/blog.html')

def contactus(request):
    return render(request,'app/contactus.html')


def confirmpayment(request):
    return render(request,'app/confirmpayment.html')



def register(request):
    form = CreateUserForm()
    if request.method == "POST":
        form = CreateUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            Customer.objects.create(user=user, name=user.username)

            request.session['pending_user'] = user.username
            return redirect('verify_phone')
        else:
            print("Form errors:", form.errors)
            messages.error(request, "Registration failed. Please check the form.")

    context = {'form': form,
               'active_form': 'signup',
               }
    return render(request, 'app/login.html', context)


def loginPage(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == "POST":
        print(request.POST)
        identifier = request.POST.get('identifier')
        password = request.POST.get('password')
        if not identifier or not password:
            messages.error(request, 'Vui lòng nhập đầy đủ thông tin.')
            return render(request, 'app/login.html')

        username = None


        if '@' in identifier:
            try:
                user_obj = User.objects.get(email=identifier)
                username = user_obj.username
            except User.DoesNotExist:
                messages.error(request, 'Email không tồn tại.')
        else:
            username = identifier  #



        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Sai tên đăng nhập/email hoặc mật khẩu.')

    return render(request, 'app/login.html',{'active_form': 'login'})

def logoutPage(request):
    logout(request)
    return redirect('home')

def change_password(request):
    if request.method == 'POST':
        form = ChangePasswordForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password changed successfully!')
            return redirect('my_account')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ChangePasswordForm(user=request.user)

    return render(request, 'my_account.html', {'form': form})







