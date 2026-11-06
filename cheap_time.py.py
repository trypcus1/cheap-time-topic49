"""
Тема 49. Выбор дешёвого времени для работы прибора.

Пользователь подбирает время запуска бытовой нагрузки по почасовому
учебному тарифу. Перебираются все допустимые начала непрерывной работы,
суммируется стоимость соответствующих часов, выбирается минимальная
(при равенстве — самое раннее начало).

Ограничения: один прибор, один день, постоянная мощность.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

HOURS_IN_DAY = 24
HOUR_NAMES = [f"{h:02d}:00-{h + 1:02d}:00" for h in range(HOURS_IN_DAY)]


# ----------------
# Структуры данных
# ----------------
@dataclass
class Device:
    """Прибор: название и постоянная мощность (кВт)."""
    name: str
    power_kw: float

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Название прибора не может быть пустым.")
        if self.power_kw <= 0:
            raise ValueError("Мощность прибора должна быть положительной.")


@dataclass
class Tariff:
    """Почасовой тариф: 24 цены за кВт·ч."""
    prices: List[float]

    def __post_init__(self) -> None:
        if len(self.prices) != HOURS_IN_DAY:
            raise ValueError("Тариф должен содержать ровно 24 цены.")
        if any(p < 0 for p in self.prices):
            raise ValueError("Цены не могут быть отрицательными.")

    def price_at(self, hour: int) -> float:
        return self.prices[hour % HOURS_IN_DAY]


@dataclass
class LaunchWindow:
    """Разрешённое окно запуска: [start_hour, end_hour] в часах 0..24."""
    start_hour: int
    end_hour: int

    def __post_init__(self) -> None:
        if not (0 <= self.start_hour < HOURS_IN_DAY):
            raise ValueError("Начало окна должно быть в диапазоне 0..23.")
        if not (0 <= self.end_hour <= HOURS_IN_DAY):
            raise ValueError("Конец окна должен быть в диапазоне 0..24.")
        if self.end_hour <= self.start_hour:
            raise ValueError("Конец окна должен быть позже начала.")


# -----------------
# Результат расчёта
# -----------------
@dataclass
class Variant:
    """Один допустимый вариант запуска."""
    start_hour: int
    hours: List[int]
    cost: float

    @property
    def interval(self) -> str:
        end = self.start_hour + len(self.hours)
        return f"{self.start_hour:02d}:00-{end:02d}:00"

    def describe(self) -> str:
        hours_str = ", ".join(HOUR_NAMES[h] for h in self.hours)
        return f"[{self.interval}]  стоимость = {self.cost:.2f}  часы: {hours_str}"


@dataclass
class ScheduleResult:
    """Итог подбора: все варианты и рекомендуемый интервал."""
    variants: List[Variant] = field(default_factory=list)
    best: Optional[Variant] = None

    def has_solution(self) -> bool:
        return self.best is not None


# -----------------
# Основной алгоритм
# -----------------
def build_hours(start_hour: int, duration: int) -> List[int]:
    """Часы непрерывной работы, начиная со start_hour (без перехода через сутки)."""
    return [start_hour + k for k in range(duration)]


def variant_cost(tariff: Tariff, device: Device, hours: List[int]) -> float:
    """Стоимость работы: мощность × сумма цен часов."""
    return device.power_kw * sum(tariff.price_at(h) for h in hours)


def find_cheap_schedule(
    tariff: Tariff,
    device: Device,
    duration: int,
    window: LaunchWindow,
) -> ScheduleResult:
    """
    Перебирает все допустимые начала непрерывной работы внутри окна.
    Возвращает все варианты и лучший (минимальная цена, при равенстве — самое
    раннее начало).
    """
    if not (1 <= duration <= HOURS_IN_DAY):
        raise ValueError("Длительность должна быть от 1 до 24 часов.")

    result = ScheduleResult()
    last_start = window.end_hour - duration  # начало, при котором работа ещё в окне

    if last_start < window.start_hour:
        return result  # окно короче длительности — решений нет

    for start in range(window.start_hour, last_start + 1):
        hours = build_hours(start, duration)
        cost = variant_cost(tariff, device, hours)
        result.variants.append(Variant(start, hours, cost))

    # Минимум по цене; при равенстве — самое раннее начало (min по ключу)
    result.best = min(result.variants, key=lambda v: (v.cost, v.start_hour))
    return result


# ------------
# Ввод / вывод
# ------------
def read_float(prompt: str) -> float:
    while True:
        raw = input(prompt).strip().replace(",", ".")
        try:
            return float(raw)
        except ValueError:
            print("  ! Введите число, например 3.5")


def read_int(prompt: str, low: int, high: int) -> int:
    while True:
        raw = input(prompt).strip()
        try:
            value = int(raw)
            if low <= value <= high:
                return value
            print(f"  ! Допустимый диапазон: {low}..{high}")
        except ValueError:
            print("  ! Введите целое число.")


def read_prices() -> List[float]:
    print("\nВведите 24 цены тарифа (можно через пробел/запятую или по одной).")
    prices: List[float] = []
    while len(prices) < HOURS_IN_DAY:
        raw = input(f"  Часы {len(prices):02d}-{len(prices) + 1:02d}: ").strip()
        parts = raw.replace(";", " ").replace(",", " ").split()
        for part in parts:
            try:
                prices.append(float(part))
            except ValueError:
                print("  ! Пропущено нечисловое значение.")
            if len(prices) == HOURS_IN_DAY:
                break
    return prices


def print_variants(result: ScheduleResult, device: Device) -> None:
    print("\n" + "=" * 72)
    print(f"Все допустимые варианты для прибора «{device.name}» "
          f"(мощность {device.power_kw:g} кВт):")
    print("=" * 72)
    if not result.has_solution():
        print("Нет допустимых вариантов: окно короче длительности работы.")
        return
    for idx, variant in enumerate(result.variants, start=1):
        print(f"{idx:>2}. {variant.describe()}")

    best = result.best
    print("-" * 72)
    print(f"Рекомендуемый интервал: {best.interval}")
    print(f"Минимальная стоимость: {best.cost:.2f}")
    print("=" * 72)


# -----------------------
# Демонстрационные данные
# -----------------------
def demo_data() -> Tuple[Tariff, Device, int, LaunchWindow]:
    # Ночью дешевле, днём дороже; два дешёвых часа разделены дорогим.
    prices = [
        2.5, 2.4, 2.3, 2.2, 2.1, 2.0,   # 00-06
        3.5, 5.0, 6.0, 6.5, 6.0, 5.5,   # 06-12
        5.0, 4.5, 4.0, 4.2, 4.8, 5.5,   # 12-18
        6.0, 5.0, 4.0, 3.0, 2.0, 1.5,   # 18-24
    ]
    tariff = Tariff(prices)
    device = Device("Стиральная машина", 2.0)
    duration = 2
    window = LaunchWindow(start_hour=20, end_hour=24)
    return tariff, device, duration, window


# ----
# Меню
# ----
def run_demo() -> None:
    tariff, device, duration, window = demo_data()
    print("\nДемонстрационный сценарий:")
    print(f"  Прибор: {device.name}, мощность {device.power_kw:g} кВт")
    print(f"  Длительность: {duration} ч")
    print(f"  Окно запуска: {window.start_hour:02d}:00-{window.end_hour:02d}:00")
    result = find_cheap_schedule(tariff, device, duration, window)
    print_variants(result, device)


def run_manual() -> None:
    print("\nРучной ввод данных")
    name = input("  Название прибора: ").strip() or "Прибор"
    power = read_float("  Мощность, кВт: ")
    duration = read_int("  Длительность работы, ч (1..24): ", 1, HOURS_IN_DAY)
    start = read_int("  Начало окна запуска, ч (0..23): ", 0, 23)
    end = read_int(f"  Конец окна запуска, ч ({start + 1}..24): ", start + 1, 24)
    prices = read_prices()

    try:
        tariff = Tariff(prices)
        device = Device(name, power)
        window = LaunchWindow(start, end)
        result = find_cheap_schedule(tariff, device, duration, window)
    except ValueError as exc:
        print(f"\nОшибка входных данных: {exc}")
        return

    print_variants(result, device)


def main() -> None:
    print("=" * 72)
    print(" Тема 49. Выбор дешёвого времени для работы прибора")
    print("=" * 72)
    while True:
        print("\nМеню:")
        print("  1 — демонстрационный расчёт")
        print("  2 — ручной ввод данных")
        print("  0 — выход")
        choice = input("Выбор: ").strip()
        if choice == "1":
            run_demo()
        elif choice == "2":
            run_manual()
        elif choice == "0":
            print("До свидания!")
            break
        else:
            print("  ! Неверный пункт меню.")


if __name__ == "__main__":
    main()
