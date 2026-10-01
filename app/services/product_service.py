from app.schemas import ProductCreate, ProductResponse, ProductUpdate

# In-memory storage: resets whenever the application restarts.
# Every product stores the ID of the user who owns it, and every function
# below only touches products owned by the given user_id.
_products: dict[int, ProductResponse] = {}
_next_id = 1


def reset_products() -> None:
    global _next_id
    _products.clear()
    _next_id = 1


def _get_owned(user_id: int, product_id: int) -> ProductResponse | None:
    product = _products.get(product_id)
    if product is None or product.user_id != user_id:
        return None
    return product


def list_products(user_id: int) -> list[ProductResponse]:
    return [p for p in _products.values() if p.user_id == user_id]


def get_product(user_id: int, product_id: int) -> ProductResponse | None:
    return _get_owned(user_id, product_id)


def create_product(user_id: int, data: ProductCreate) -> ProductResponse:
    global _next_id
    product = ProductResponse(id=_next_id, user_id=user_id, **data.model_dump())
    _products[product.id] = product
    _next_id += 1
    return product


def replace_product(
    user_id: int, product_id: int, data: ProductCreate
) -> ProductResponse | None:
    if _get_owned(user_id, product_id) is None:
        return None
    product = ProductResponse(id=product_id, user_id=user_id, **data.model_dump())
    _products[product_id] = product
    return product


def update_product(
    user_id: int, product_id: int, data: ProductUpdate
) -> ProductResponse | None:
    product = _get_owned(user_id, product_id)
    if product is None:
        return None
    updated = product.model_copy(update=data.model_dump(exclude_unset=True))
    _products[product_id] = updated
    return updated


def delete_product(user_id: int, product_id: int) -> bool:
    if _get_owned(user_id, product_id) is None:
        return False
    del _products[product_id]
    return True


def delete_all_products(user_id: int) -> int:
    ids = [p.id for p in list_products(user_id)]
    for product_id in ids:
        del _products[product_id]
    return len(ids)
