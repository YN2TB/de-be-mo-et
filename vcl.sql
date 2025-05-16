CREATE DATABASE IF NOT EXISTS BankingDB;
USE BankingDB;

-- Branches
CREATE TABLE Branches (
    BranchID INT PRIMARY KEY AUTO_INCREMENT,
    BranchName VARCHAR(100),
    Address VARCHAR(255)
);

-- Employees
CREATE TABLE Employees (
    EmployeeID INT PRIMARY KEY AUTO_INCREMENT,
    EmployeeName VARCHAR(100),
    Position VARCHAR(50),
    BranchID INT,
    FOREIGN KEY (BranchID) REFERENCES Branches(BranchID)
);

-- Services
CREATE TABLE Services (
    ServiceID INT PRIMARY KEY AUTO_INCREMENT,
    ServiceName VARCHAR(100),
    Description TEXT,
    ServiceFee DECIMAL(10,2),
    EmployeeID INT,
    FOREIGN KEY (EmployeeID) REFERENCES Employees(EmployeeID)
);

-- Customers
CREATE TABLE Customers (
    CustomerID INT PRIMARY KEY AUTO_INCREMENT,
    CustomerName VARCHAR(100),
    PhoneNumber VARCHAR(20),
    Address VARCHAR(255)
);

-- Login Credentials
CREATE TABLE LoginCredentials (
    CustomerID INT PRIMARY KEY,
    Username VARCHAR(50) UNIQUE,
    Password VARCHAR(255),
    LastLogin DATETIME,
    IsLocked BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (CustomerID) REFERENCES Customers(CustomerID)
);

-- Accounts
CREATE TABLE Accounts (
    AccountID INT PRIMARY KEY AUTO_INCREMENT,
    CustomerID INT,
    Balance DECIMAL(15,2),
    OpenDate DATE,
    FOREIGN KEY (CustomerID) REFERENCES Customers(CustomerID)
);

-- Transactions
CREATE TABLE Transactions (
    TransactionID INT PRIMARY KEY AUTO_INCREMENT,
    AccountID INT,
    TransactionDate DATETIME,
    Amount DECIMAL(15,2),
    TransactionType VARCHAR(50),
    TransactionInfo TEXT,
    FOREIGN KEY (AccountID) REFERENCES Accounts(AccountID)
);

-- Cards
CREATE TABLE Cards (
    CardID INT PRIMARY KEY AUTO_INCREMENT,
    CustomerID INT,
    CardType VARCHAR(50),
    CardSeries VARCHAR(50),
    ExpirationDate DATE,
    CVV VARCHAR(10),
    CardStatus VARCHAR(20),
    FOREIGN KEY (CustomerID) REFERENCES Customers(CustomerID)
);

-- Card Transactions
CREATE TABLE CardTransactions (
    CardTransactionID INT PRIMARY KEY AUTO_INCREMENT,
    CardID INT,
    CardTransactionDate DATETIME,
    CardTransactionAmount DECIMAL(15,2),
    MerchantID VARCHAR(50),
    Location VARCHAR(100),
    FOREIGN KEY (CardID) REFERENCES Cards(CardID)
);

-- Loans
CREATE TABLE Loans (
    LoanAccountID INT PRIMARY KEY AUTO_INCREMENT,
    CustomerID INT,
    LoanType VARCHAR(50),
    LoanAmount DECIMAL(15,2),
    InterestRate DECIMAL(5,2),
    StartDate DATE,
    EndDate DATE,
    LoanStatus VARCHAR(50),
    OverdueDates TEXT,
    FOREIGN KEY (CustomerID) REFERENCES Customers(CustomerID)
);

-- Loan Payments
CREATE TABLE LoanPayments (
    LoanPaymentID INT PRIMARY KEY AUTO_INCREMENT,
    LoanAccountID INT,
    PaymentDate DATE,
    AmountPaid DECIMAL(15,2),
    FOREIGN KEY (LoanAccountID) REFERENCES Loans(LoanAccountID)
);

-- Customer Services
CREATE TABLE CustomerServices (
    CustomerID INT,
    ServiceID INT,
    StartDate DATE,
    EndDate DATE,
    PRIMARY KEY (CustomerID, ServiceID),
    FOREIGN KEY (CustomerID) REFERENCES Customers(CustomerID),
    FOREIGN KEY (ServiceID) REFERENCES Services(ServiceID)
);
