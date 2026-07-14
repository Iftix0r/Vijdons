from django.shortcuts import render, redirect
from .models import Order, Driver, Client

def order_create(request):
    if request.method == 'POST':
        phone_number = request.POST.get('phone_number')
        from_address = request.POST.get('from_address')
        to_address = request.POST.get('to_address')
        
        if phone_number and from_address and to_address:
            client, created = Client.objects.get_or_create(phone_number=phone_number)
            Order.objects.create(
                client=client,
                from_address=from_address,
                to_address=to_address,
                status='pending'
            )
        return redirect(request.META.get('HTTP_REFERER', 'taxi:panel_dashboard'))
    return redirect('taxi:panel_dashboard')

def driver_create(request):
    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        phone_number = request.POST.get('phone_number')
        car_model = request.POST.get('car_model')
        car_number = request.POST.get('car_number')
        if full_name and phone_number:
            Driver.objects.create(
                full_name=full_name,
                phone_number=phone_number,
                car_model=car_model,
                car_number=car_number
            )
    return redirect(request.META.get('HTTP_REFERER', 'taxi:driver_list'))

def client_create(request):
    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        phone_number = request.POST.get('phone_number')
        if phone_number:
            Client.objects.get_or_create(
                phone_number=phone_number,
                defaults={'full_name': full_name}
            )
    return redirect(request.META.get('HTTP_REFERER', 'taxi:client_list'))

def panel_dashboard(request):
    orders = Order.objects.all().order_by('-created_at')[:10]
    total_orders = Order.objects.count()
    total_drivers = Driver.objects.count()
    total_clients = Client.objects.count()
    
    context = {
        'orders': orders,
        'total_orders': total_orders,
        'total_drivers': total_drivers,
        'total_clients': total_clients,
    }
    return render(request, 'taxi/panel.html', context)

def order_list(request):
    orders = Order.objects.all().order_by('-created_at')
    return render(request, 'taxi/order_list.html', {'orders': orders})

def driver_list(request):
    drivers = Driver.objects.all()
    return render(request, 'taxi/driver_list.html', {'drivers': drivers})

def client_list(request):
    clients = Client.objects.all()
    return render(request, 'taxi/client_list.html', {'clients': clients})
