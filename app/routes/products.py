from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.dependencies import CurrentUser, get_current_user
from app.schemas import (
    DeleteAllResponse,
    ErrorResponse,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
)
from app.services import product_service

# Every product endpoint requires a valid JWT. Users only ever see their own products.
router = APIRouter(
    prefix="/products",
    tags=["Products"],
    dependencies=[Depends(get_current_user)],
    responses={401: {"model": ErrorResponse, "description": "Not authenticated"}},
)

ProductId = Path(gt=0, description="Unique product ID", examples=[1])
NOT_FOUND = {404: {"model": ErrorResponse, "description": "Product not found"}}


def _not_found(product_id: int) -> HTTPException:
    # Same 404 whether the product is missing or belongs to someone else,
    # so other users' product IDs are not revealed.
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Product with id {product_id} not found",
    )


# The trailing-slash variants keep the original "/products/" URLs working.
@router.get("", response_model=list[ProductResponse], summary="List my products")
@router.get("/", response_model=list[ProductResponse], include_in_schema=False)
def list_products(user: CurrentUser) -> list[ProductResponse]:
    """Return the products owned by the logged-in user."""
    return product_service.list_products(user.id)


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Get a product by ID",
    responses=NOT_FOUND,
)
def get_product(user: CurrentUser, product_id: int = ProductId) -> ProductResponse:
    """Return one of my products, or 404 if it does not exist or is not mine."""
    product = product_service.get_product(user.id, product_id)
    if product is None:
        raise _not_found(product_id)
    return product


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a product",
)
@router.post(
    "/",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def create_product(data: ProductCreate, user: CurrentUser) -> ProductResponse:
    """Create a product owned by the logged-in user. The owner is never read from the body."""
    return product_service.create_product(user.id, data)


@router.put(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Replace a product",
    responses=NOT_FOUND,
)
def replace_product(
    data: ProductCreate, user: CurrentUser, product_id: int = ProductId
) -> ProductResponse:
    """Replace all fields of one of my products."""
    product = product_service.replace_product(user.id, product_id, data)
    if product is None:
        raise _not_found(product_id)
    return product


@router.patch(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Partially update a product",
    responses=NOT_FOUND,
)
def update_product(
    data: ProductUpdate, user: CurrentUser, product_id: int = ProductId
) -> ProductResponse:
    """Update only the fields included in the request body."""
    product = product_service.update_product(user.id, product_id, data)
    if product is None:
        raise _not_found(product_id)
    return product


@router.delete("", response_model=DeleteAllResponse, summary="Delete all my products")
@router.delete("/", response_model=DeleteAllResponse, include_in_schema=False)
def delete_all_products(user: CurrentUser) -> DeleteAllResponse:
    """Delete every product owned by the logged-in user. Other users' products are untouched."""
    return DeleteAllResponse(deleted=product_service.delete_all_products(user.id))


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a product by ID",
    responses=NOT_FOUND,
)
def delete_product(user: CurrentUser, product_id: int = ProductId) -> None:
    """Delete one of my products, or 404 if it does not exist or is not mine."""
    if not product_service.delete_product(user.id, product_id):
        raise _not_found(product_id)
